#!/usr/bin/env python3

"""
Persistent Browser Server - Stays alive, allows reconnection
Based on OpenClaw pattern but simpler (HTTP only, no WebSockets needed)
"""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime
from aiohttp import web
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from dataclasses import asdict

from browser_interactions import format_aria_tree, get_dom_snapshot
from enhanced_browser_interactions import (
    AriaRefMapper,
    PageObserver,
    NetworkMonitor,
    get_llm_snapshot
)

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
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        """Setup HTTP routes (like OpenClaw)"""
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/status', self.handle_status)
        self.app.router.add_post('/navigate', self.handle_navigate)
        self.app.router.add_get('/snapshot', self.handle_snapshot)
        self.app.router.add_get('/html', self.handle_html)
        self.app.router.add_get('/html-clean', self.handle_html_clean)
        self.app.router.add_post('/click', self.handle_click)
        self.app.router.add_post('/fill', self.handle_fill)
        self.app.router.add_post('/keyboard', self.handle_keyboard)  # OpenClaw pattern
        self.app.router.add_post('/evaluate', self.handle_evaluate)  # JavaScript execution
        self.app.router.add_post('/save-session', self.handle_save_session)
        self.app.router.add_get('/screenshot', self.handle_screenshot)

    async def start_browser(self):
        """Start browser (once) with anti-detection for Gmail/Google"""
        logger.info("🚀 Starting browser with anti-detection...")

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
            logger.info(f"📂 Loading session: {self.session_file}")
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

        # Add realistic HTTP headers (removed Cache-Control to avoid CORS errors)
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
        logger.info("✅ Stealth mode applied")

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

        logger.info("✅ Browser ready")

    # ========================================================================
    # HTTP Handlers (LLM calls these)
    # ========================================================================

    async def handle_health(self, request):
        """Health check"""
        return web.json_response({"status": "ok", "browser_alive": self.browser is not None})

    async def handle_status(self, request):
        """Get current browser status"""
        if not self.page:
            return web.json_response({"error": "No page"}, status=400)

        return web.json_response({
            "url": self.page.url,
            "title": await self.page.title(),
            "has_session": Path(self.session_file).exists()
        })

    async def handle_navigate(self, request):
        """Navigate to URL"""
        data = await request.json()
        url = data.get('url')

        if not url:
            return web.json_response({"error": "url required"}, status=400)

        logger.info(f"→ Navigating to: {url}")
        # Use 'domcontentloaded' instead of 'networkidle' for speed (2-3x faster)
        await self.page.goto(url, wait_until='domcontentloaded')
        # No sleep - page is ready after goto completes

        return web.json_response({
            "success": True,
            "url": self.page.url,
            "title": await self.page.title()
        })

    async def handle_snapshot(self, request):
        """
        Get page snapshot (ARIA + DOM + console + network)
        This is what the LLM sees!
        """
        logger.info("📸 Getting snapshot...")

        # Get ARIA and DOM
        aria_tree = await format_aria_tree(self.page, limit=500)
        dom_tree = await get_dom_snapshot(self.page, limit=800)

        # Build ref mapper
        self.ref_mapper = AriaRefMapper()
        await self.ref_mapper.build_map(self.page, [asdict(node) for node in aria_tree])

        # Get comprehensive snapshot
        snapshot = await get_llm_snapshot(
            self.page,
            [asdict(node) for node in aria_tree],
            dom_tree,
            self.observer,
            self.network
        )

        logger.info(f"✅ Snapshot ready: {len(aria_tree)} ARIA nodes")

        return web.json_response(snapshot)

    async def handle_click(self, request):
        """Click element by CSS selector"""
        data = await request.json()
        selector = data.get('selector')

        if not selector:
            return web.json_response({"error": "selector required"}, status=400)

        try:
            logger.info(f"🖱️  Clicking: {selector}")
            await self.page.click(selector, timeout=5000)
            # Wait for DOM to be ready instead of arbitrary sleep
            await self.page.wait_for_load_state('domcontentloaded')

            return web.json_response({"success": True})
        except Exception as e:
            logger.error(f"❌ Click failed: {e}")
            return web.json_response({"error": str(e)}, status=400)

    async def handle_fill(self, request):
        """Fill text into field - OpenClaw pattern for complex forms"""
        data = await request.json()
        selector = data.get('selector')
        text = data.get('text')
        slowly = data.get('slowly', False)  # OpenClaw pattern for contenteditable
        delay_ms = data.get('delay', 15)  # Configurable delay (default 15ms, was 50ms)

        if not selector or text is None:
            return web.json_response({"error": "selector and text required"}, status=400)

        try:
            logger.info(f"⌨️  Filling: {selector} (slowly={slowly}, delay={delay_ms}ms)")

            # OpenClaw pattern: slowly=True for contenteditable divs
            if slowly:
                # Click to focus first
                await self.page.click(selector, timeout=8000)
                await asyncio.sleep(0.1)  # Reduced from 0.2s
                # Clear existing text
                await self.page.keyboard.press("Control+A")
                await asyncio.sleep(0.05)  # Reduced from 0.1s
                # Type slowly instead of fill (works for contenteditable)
                # OPTIMIZED: 15ms default (was 50ms) = 3.3x faster
                await self.page.keyboard.type(text, delay=delay_ms)
            else:
                # Standard fill for normal inputs
                await self.page.fill(selector, text)

            return web.json_response({"success": True})
        except Exception as e:
            logger.error(f"❌ Fill failed: {e}")
            return web.json_response({"error": str(e)}, status=400)

    async def handle_keyboard(self, request):
        """Handle keyboard press - OpenClaw pattern"""
        data = await request.json()
        key = data.get('key')
        delay_ms = data.get('delay', 0)

        if not key:
            return web.json_response({"error": "key required"}, status=400)

        try:
            logger.info(f"⌨️  Keyboard press: {key}")
            await self.page.keyboard.press(key, delay=max(0, delay_ms))
            return web.json_response({"success": True})
        except Exception as e:
            logger.error(f"❌ Keyboard press failed: {e}")
            return web.json_response({"error": str(e)}, status=400)

    async def handle_evaluate(self, request):
        """Execute JavaScript in page context"""
        data = await request.json()
        script = data.get('script')

        if not script:
            return web.json_response({"error": "script required"}, status=400)

        try:
            logger.info(f"🔧 Evaluating JS: {script[:100]}...")
            result = await self.page.evaluate(script)
            return web.json_response({"success": True, "result": result})
        except Exception as e:
            logger.error(f"❌ JS evaluation failed: {e}")
            return web.json_response({"error": str(e)}, status=400)

    async def handle_save_session(self, request):
        """Save browser session"""
        if not self.context:
            return web.json_response({"error": "No context"}, status=400)

        Path(self.session_file).parent.mkdir(parents=True, exist_ok=True)
        await self.context.storage_state(path=self.session_file)

        logger.info(f"💾 Session saved: {self.session_file}")

        return web.json_response({"success": True, "path": self.session_file})

    async def handle_screenshot(self, request):
        """Take screenshot"""
        path = "artifacts/screenshot.png"
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        await self.page.screenshot(path=path)
        logger.info(f"📸 Screenshot: {path}")

        return web.json_response({"success": True, "path": path})

    async def handle_html(self, request):
        """
        Get current page HTML (raw)
        This is what the LLM needs to see!
        """
        logger.info("📄 Getting page HTML...")

        html = await self.page.content()

        return web.json_response({
            "success": True,
            "url": self.page.url,
            "title": await self.page.title(),
            "html": html,
            "html_length": len(html)
        })

    async def handle_html_clean(self, request):
        """
        Get cleaned/simplified HTML for LLM understanding
        Removes scripts, styles, keeps structure
        """
        logger.info("📄 Getting cleaned HTML...")

        # Get HTML and clean it
        html = await self.page.evaluate("""
        () => {
            // Clone the document
            const clone = document.documentElement.cloneNode(true);

            // Remove scripts, styles, and other noise
            const removeTags = ['script', 'style', 'noscript', 'svg', 'path'];
            removeTags.forEach(tag => {
                clone.querySelectorAll(tag).forEach(el => el.remove());
            });

            // Remove comments
            const removeComments = (node) => {
                for (let i = node.childNodes.length - 1; i >= 0; i--) {
                    const child = node.childNodes[i];
                    if (child.nodeType === 8) { // Comment node
                        node.removeChild(child);
                    } else if (child.nodeType === 1) { // Element node
                        removeComments(child);
                    }
                }
            };
            removeComments(clone);

            // Get the cleaned HTML
            return clone.outerHTML;
        }
        """)

        return web.json_response({
            "success": True,
            "url": self.page.url,
            "title": await self.page.title(),
            "html": html,
            "html_length": len(html)
        })

    # ========================================================================
    # Server lifecycle
    # ========================================================================

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
        logger.info("✅ PERSISTENT BROWSER SERVER RUNNING")
        logger.info("="*80)
        logger.info(f"HTTP Server: http://localhost:{self.port}")
        logger.info("")
        logger.info("Endpoints:")
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
            logger.info("🛑 Browser closed")


# ============================================================================
# Main entry point
# ============================================================================

async def main(headless=False):
    server = PersistentBrowserServer(port=9222, headless=headless)

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("\n⚠️  Shutting down...")
        asyncio.create_task(server.stop())
        loop.stop()

    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    # Start server
    await server.start()

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Persistent Browser Server for Cloud Run')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode (for Cloud Run deployment)')
    args = parser.parse_args()

    print(f"🚀 Starting browser server ({'HEADLESS' if args.headless else 'HEADED'} mode)")
    asyncio.run(main(headless=args.headless))
