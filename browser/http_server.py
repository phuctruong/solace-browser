#!/usr/bin/env python3

"""
HTTP Server module - Persistent browser server wrapper

This is the thin HTTP layer that wraps the core browser functionality.
All endpoint handlers are in handlers.py
"""

import asyncio
import logging
import signal
from pathlib import Path
from aiohttp import web
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
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


class PersistentBrowserServer:
    """
    Browser server that stays alive
    LLM can connect/disconnect and continue where it left off
    """

    def __init__(self, port=9223, headless=False):
        self.port = port
        self.headless = headless  # Cloud Run support
        self.browser = None
        self.context = None
        self.page = None
        self.ref_mapper = None
        self.observer = None
        self.network = None
        self.session_file = "artifacts/linkedin_session.json"
        self.rate_limiter = RateLimiter()
        self.registry = RegistryChecker()
        self.app = web.Application()
        setup_handlers(self.app, self)

    async def start_browser(self):
        """Start browser (once) with anti-detection for Gmail/Google"""
        logger.info("Starting browser with anti-detection...")

        playwright = await async_playwright().start()

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

            # Performance
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-webgl',

            # Privacy
            '--no-first-run',
            '--no-default-browser-check',
            '--no-pings',

            # User agent
            '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        ]

        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=chrome_args
        )

        # Load session if exists
        context_options = {}
        if Path(self.session_file).exists():
            logger.info(f"Loading session: {self.session_file}")
            context_options['storage_state'] = self.session_file

        # Add realistic user-agent (real Chrome on Linux)
        context_options['user_agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

        # Set realistic viewport (most common desktop resolution)
        context_options['viewport'] = {'width': 1920, 'height': 1080}

        # Device scale factor (for retina displays)
        context_options['device_scale_factor'] = 1

        # Geolocation (optional, can help bypass some checks)
        context_options['geolocation'] = {'latitude': 42.3601, 'longitude': -71.0589}  # Boston
        context_options['permissions'] = ['geolocation']

        # Add realistic HTTP headers
        context_options['extra_http_headers'] = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1',
        }

        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

        # Apply playwright-stealth (comprehensive anti-detection)
        stealth = Stealth(
            navigator_languages_override=('en-US', 'en'),
            navigator_platform_override='Linux x86_64',
            navigator_user_agent_override='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        await stealth.apply_stealth_async(self.page)
        logger.info("Stealth mode applied")

        # Advanced anti-detection: Override multiple automation signals
        await self.page.add_init_script("""
            // 1. Hide webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 1b. Override User-Agent Client Hints (CRITICAL: hides "HeadlessChrome")
            Object.defineProperty(navigator, 'userAgentData', {
                get: () => ({
                    brands: [
                        { brand: 'Google Chrome', version: '131' },
                        { brand: 'Chromium', version: '131' },
                        { brand: 'Not_A Brand', version: '24' }
                    ],
                    mobile: false,
                    platform: 'Linux'
                })
            });

            // 2. Override plugins to look like real Chrome
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        name: 'Chrome PDF Plugin',
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer',
                        length: 1
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        description: '',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                        length: 1
                    },
                    {
                        name: 'Native Client',
                        description: '',
                        filename: 'internal-nacl-plugin',
                        length: 2
                    }
                ]
            });

            // 3. Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // 4. Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // 5. Add Chrome runtime (makes it look like real Chrome)
            window.chrome = {
                runtime: {}
            };

            // 6. Override toString to hide proxy
            const elementDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
            Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
                ...elementDescriptor,
                get: function() {
                    if (this.id === 'modernizr') {
                        return 1;
                    }
                    return elementDescriptor.get.apply(this);
                }
            });

            // 7. Canvas fingerprinting - add subtle noise
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                // Add minimal noise to avoid detection but maintain functionality
                const context = this.getContext('2d');
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    // Add tiny random noise (0-2) to RGB
                    imageData.data[i] += Math.floor(Math.random() * 3);
                    imageData.data[i + 1] += Math.floor(Math.random() * 3);
                    imageData.data[i + 2] += Math.floor(Math.random() * 3);
                }
                context.putImageData(imageData, 0, 0);
                return originalToDataURL.apply(this, arguments);
            };

            // 8. WebGL fingerprinting evasion
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // Fake vendor/renderer to look like real Chrome
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.apply(this, arguments);
            };

            // 9. Override Date to prevent timezone detection
            const originalDate = Date;
            Date = class extends originalDate {
                getTimezoneOffset() {
                    return 300; // EST timezone
                }
            };

            // 10. Add connection info
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 100,
                    downlink: 10,
                    saveData: false
                })
            });
        """)

        # Setup monitoring
        self.observer = PageObserver(self.page)
        self.network = NetworkMonitor(self.page)

        logger.info("Browser ready")

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

    async def stop(self):
        """Cleanup"""
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
