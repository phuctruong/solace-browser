#!/usr/bin/env python3

"""
HTTP Server module - Persistent browser server wrapper

This is the thin HTTP layer that wraps the core browser functionality.
All endpoint handlers are in handlers.py
"""

import asyncio
import logging
import signal
import os
from pathlib import Path
from aiohttp import web
from playwright.async_api import async_playwright
from dataclasses import asdict

from browser.core import format_aria_tree, get_dom_snapshot
from browser.advanced import AriaRefMapper, PageObserver, NetworkMonitor, get_llm_snapshot
from browser.handlers import setup_handlers
from rate_limiter import RateLimiter
from registry_checker import RegistryChecker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('browser-server')

try:
    from playwright_stealth import Stealth  # type: ignore
except Exception:
    Stealth = None
    logger.warning("playwright_stealth not installed; continuing without stealth layer")


class PersistentBrowserServer:
    """
    Browser server that stays alive
    LLM can connect/disconnect and continue where it left off
    """

    def __init__(
        self,
        port=9223,
        headless=False,
        session_file: str | None = None,
        autosave_seconds: int | None = None,
        user_data_dir: str | None = None,
    ):
        self.port = port
        self.headless = headless  # Cloud Run support
        self._playwright = None
        self._persistent_context = False
        self.browser = None
        self.context = None
        self.page = None
        self.ref_mapper = None
        self.observer = None
        self.network = None
        # Canonical shared storage_state file. Many older scripts used
        # artifacts/linkedin_session.json; we keep that working via env/flags,
        # but default to a single stable file so restarts keep logins.
        self.session_file = session_file or os.getenv("SOLACE_SESSION_FILE") or "artifacts/solace_session.json"
        # Prefer a shared Chrome profile directory to preserve logins/cookies even
        # if the process is restarted without a clean shutdown.
        self.user_data_dir = user_data_dir
        if self.user_data_dir is None:
            self.user_data_dir = os.getenv("SOLACE_USER_DATA_DIR")
        self.autosave_seconds = autosave_seconds
        if self.autosave_seconds is None:
            env_autosave = os.getenv("SOLACE_AUTOSAVE_SECONDS")
            if env_autosave:
                try:
                    self.autosave_seconds = int(env_autosave)
                except ValueError:
                    logger.warning(f"Invalid SOLACE_AUTOSAVE_SECONDS={env_autosave!r}; ignoring")
                    self.autosave_seconds = None
        self._autosave_task: asyncio.Task | None = None
        self.rate_limiter = RateLimiter()
        self.registry = RegistryChecker()
        self.app = web.Application()
        setup_handlers(self.app, self)

    async def save_session(self):
        """Save browser context cookies/localStorage to the configured storage_state file."""
        if not self.context:
            return
        try:
            Path(self.session_file).parent.mkdir(parents=True, exist_ok=True)
            await self.context.storage_state(path=self.session_file)
            logger.info(f"Session saved: {self.session_file}")
        except Exception as e:
            logger.warning(f"Failed to save session to {self.session_file}: {e}")

    async def start_browser(self):
        """Start browser (once) with anti-detection for Gmail/Google"""
        logger.info("Starting browser with anti-detection...")

        playwright = await async_playwright().start()
        self._playwright = playwright

        # Advanced anti-detection Chrome args (bypass Google's bot detection)
        chrome_args = [
            # Core anti-detection
            '--disable-blink-features=AutomationControlled',
            '--exclude-switches=enable-automation',
            '--disable-dev-shm-usage',

            # Sandbox (needed for headless)
            '--no-sandbox',
            '--disable-setuid-sandbox',

            # Make it look like normal browser
            '--disable-infobars',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-features=TranslateUI',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-sync',

            # Privacy
            '--no-first-run',
            '--no-default-browser-check',
            '--no-pings',
        ]

        # Context options (shared between ephemeral and persistent contexts)
        context_options = {}

        # Load storage_state if available. This is helpful even for persistent profiles
        # because it can "seed" a new profile dir with an existing login state.
        if Path(self.session_file).exists():
            logger.info(f"Loading session: {self.session_file}")
            context_options["storage_state"] = self.session_file

        # Set realistic viewport (most common desktop resolution)
        context_options['viewport'] = {'width': 1920, 'height': 1080}

        # Device scale factor (for retina displays)
        context_options['device_scale_factor'] = 1

        # Geolocation (optional, can help bypass some checks)
        context_options['geolocation'] = {'latitude': 42.3601, 'longitude': -71.0589}  # Boston
        context_options['permissions'] = ['geolocation']

        # Add realistic HTTP headers
        context_options['extra_http_headers'] = {
            'Accept-Language': 'en-US,en;q=0.9',
            # NOTE: Do not add non-safelisted headers globally.
            # Some sites (e.g. reddit.com) load cross-origin ES modules from a CDN
            # (redditstatic.com). A non-safelisted header triggers CORS preflight
            # (OPTIONS) on those module fetches, which can fail and break the page.
        }

        # Prefer system Chrome when available (more "real" in headed mode),
        # but fall back to Playwright's bundled Chromium if the channel is unavailable.
        #
        # If a user_data_dir is provided, use a persistent context so login sessions
        # survive restarts even without explicit storage_state saves.
        user_data_dir = (str(self.user_data_dir).strip() if self.user_data_dir else "")
        if user_data_dir:
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
            self._persistent_context = True
            # NOTE: playwright's launch_persistent_context() does not accept storage_state
            # in some versions. The persistent profile directory is the source of truth.
            # We still support storage_state for ephemeral contexts below.
            persistent_context_options = dict(context_options)
            persistent_context_options.pop("storage_state", None)
            launch_kwargs = {"headless": self.headless, "args": chrome_args, **persistent_context_options}
            try:
                self.context = await playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    channel="chrome",
                    **launch_kwargs,
                )
                self.browser = self.context.browser
                logger.info(f"Launched persistent context: channel=chrome user_data_dir={user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to launch persistent context with channel=chrome; falling back: {e}")
                self.context = await playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    **launch_kwargs,
                )
                self.browser = self.context.browser
                logger.info(f"Launched persistent context: bundled chromium user_data_dir={user_data_dir}")
        else:
            launch_kwargs = {"headless": self.headless, "args": chrome_args}
            try:
                self.browser = await playwright.chromium.launch(channel="chrome", **launch_kwargs)
                logger.info("Launched browser: channel=chrome")
            except Exception as e:
                logger.warning(f"Failed to launch channel=chrome; falling back to bundled Chromium: {e}")
                self.browser = await playwright.chromium.launch(**launch_kwargs)

            self.context = await self.browser.new_context(**context_options)

        # Ensure we have a page.
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        # Apply playwright-stealth (comprehensive anti-detection) if available.
        if Stealth is not None:
            stealth = Stealth(
                navigator_languages_override=('en-US', 'en'),
                navigator_platform_override='Linux x86_64',
            )
            await stealth.apply_stealth_async(self.page)
            logger.info("Stealth mode applied")
        else:
            logger.info("Stealth mode skipped (playwright_stealth missing)")

        # Advanced anti-detection: Override automation signals.
        #
        # Important: keep these shims compatible with modern sites. In particular,
        # overriding `navigator.userAgentData` with a plain object (missing
        # getHighEntropyValues()) can break site bootstraps and cause "unstyled" pages.
        scripts = []
        scripts.append(r"""
            // Hide webdriver.
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Plugins: look more like real Chrome.
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer', length: 1 },
                    { name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', length: 1 },
                    { name: 'Native Client', description: '', filename: 'internal-nacl-plugin', length: 2 }
                ]
            });

            // Languages.
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

            // Permissions.
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters)
            );

            // Chrome runtime marker.
            window.chrome = window.chrome || { runtime: {} };

            // OffsetHeight modernizr quirk.
            const elementDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
            if (elementDescriptor && elementDescriptor.get) {
                Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
                    ...elementDescriptor,
                    get: function() {
                        if (this.id === 'modernizr') return 1;
                        return elementDescriptor.get.apply(this);
                    }
                });
            }

            // Canvas fingerprinting: subtle noise.
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {
                try {
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] += Math.floor(Math.random() * 3);
                            imageData.data[i + 1] += Math.floor(Math.random() * 3);
                            imageData.data[i + 2] += Math.floor(Math.random() * 3);
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                } catch (_) {}
                return originalToDataURL.apply(this, arguments);
            };

            // WebGL fingerprinting evasion.
            const hasWebGL = (typeof WebGLRenderingContext !== 'undefined') && WebGLRenderingContext && WebGLRenderingContext.prototype;
            const getParameter = hasWebGL && WebGLRenderingContext.prototype.getParameter;
            if (getParameter) {
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                    return getParameter.apply(this, arguments);
                };
            }

            // Timezone: override the prototype method instead of replacing Date entirely.
            const originalTz = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() { return 300; }; // EST

            // Connection info.
            Object.defineProperty(navigator, 'connection', {
                get: () => ({ effectiveType: '4g', rtt: 100, downlink: 10, saveData: false })
            });
        """)

        if self.headless:
            # UA Client Hints: modern Chrome already provides navigator.userAgentData.
            # Overriding it can cause subtle site breakage (e.g., mismatched UA vs UAData),
            # so only shim when it's missing.
            scripts.append(r"""
                (function() {
                    try {
                        if ('userAgentData' in navigator && navigator.userAgentData) return;
                    } catch (_) {}

                    const ua = navigator.userAgent || '';
                    const m = ua.match(/Chrome\/(\d+)\.(\d+)\.(\d+)\.(\d+)/);
                    const major = (m && m[1]) ? m[1] : '0';
                    const full = m ? `${m[1]}.${m[2]}.${m[3]}.${m[4]}` : '';

                    Object.defineProperty(navigator, 'userAgentData', {
                        get: () => ({
                            brands: [
                                { brand: 'Google Chrome', version: major },
                                { brand: 'Chromium', version: major },
                                { brand: 'Not_A Brand', version: '24' }
                            ],
                            mobile: false,
                            platform: 'Linux',
                            getHighEntropyValues: async (hints) => {
                                const out = {};
                                (hints || []).forEach((h) => {
                                    if (h === 'platform') out.platform = 'Linux';
                                    if (h === 'platformVersion') out.platformVersion = '6.5.0';
                                    if (h === 'architecture') out.architecture = 'x86';
                                    if (h === 'model') out.model = '';
                                    if (h === 'uaFullVersion') out.uaFullVersion = full;
                                    if (h === 'fullVersionList') {
                                        out.fullVersionList = [
                                            { brand: 'Google Chrome', version: full },
                                            { brand: 'Chromium', version: full },
                                            { brand: 'Not_A Brand', version: '24.0.0.0' }
                                        ];
                                    }
                                });
                                return out;
                            },
                            toJSON: function() { return { brands: this.brands, mobile: this.mobile, platform: this.platform }; }
                        })
                    });
                })();
            """)

        await self.page.add_init_script("\n".join(scripts))

        # Setup monitoring
        self.observer = PageObserver(self.page)
        self.network = NetworkMonitor(self.page)

        logger.info("Browser ready")

    async def _autosave_loop(self):
        assert self.autosave_seconds is not None
        assert self.autosave_seconds > 0
        while True:
            await asyncio.sleep(self.autosave_seconds)
            await self.save_session()

    async def start(self):
        """Start the server (keeps running)"""
        # Start browser first
        await self.start_browser()

        # Start HTTP server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()

        logger.info("="*80)
        logger.info("PERSISTENT BROWSER SERVER RUNNING")
        logger.info("="*80)
        logger.info(f"HTTP Server: http://localhost:{self.port}")
        logger.info("")
        logger.info("STANDARD ENDPOINTS:")
        logger.info("  GET  /health           - Health check")
        logger.info("  GET  /status           - Current browser status")
        logger.info("  POST /navigate         - Navigate to URL")
        logger.info("  GET  /snapshot         - Get page snapshot (ARIA + DOM + console)")
        logger.info("  POST /click            - Click element")
        logger.info("  POST /fill             - Fill text field")
        logger.info("  POST /save-session     - Save browser session")
        logger.info("  GET  /screenshot       - Take screenshot")
        logger.info("")
        logger.info("Browser stays open - you can disconnect and reconnect anytime")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*80)

        if self.autosave_seconds and self.autosave_seconds > 0:
            if not self.headless:
                logger.warning(
                    "Autosave is enabled in headed mode. This can disrupt interactive typing; "
                    "prefer autosave=0 and use POST /api/save-session after login."
                )
            logger.info(f"Autosave enabled: every {self.autosave_seconds}s -> {self.session_file}")
            self._autosave_task = asyncio.create_task(self._autosave_loop())

    async def stop(self):
        """Cleanup"""
        if self._autosave_task:
            self._autosave_task.cancel()
            self._autosave_task = None

        # Best-effort save before shutting down so a manual login persists across restarts.
        await self.save_session()

        try:
            if self.context:
                await self.context.close()
                logger.info("Context closed")
        except Exception as e:
            logger.warning(f"Failed to close context: {e}")

        # For non-persistent contexts, closing the Browser is still needed.
        if self.browser and not self._persistent_context:
            try:
                await self.browser.close()
                logger.info("Browser closed")
            except Exception as e:
                logger.warning(f"Failed to close browser: {e}")

        if self._playwright is not None:
            try:
                await self._playwright.stop()
                logger.info("Playwright stopped")
            except Exception as e:
                logger.warning(f"Failed to stop Playwright: {e}")
            finally:
                self._playwright = None
