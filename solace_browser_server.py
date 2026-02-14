#!/usr/bin/env python3

"""
SOLACE BROWSER - Custom Headless Browser with CDP Protocol
Option C: Headless core + optional debugging UI

Features:
- Real browser automation (Chromium-based)
- Chrome DevTools Protocol (CDP) support
- Headless by default
- Optional web-based debugging UI
- Screenshot and DOM snapshot capture
- Full page navigation and interaction
"""

import asyncio
import json
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, Optional, Any
import uuid
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("ERROR: Playwright not installed")
    print("Install with: pip install playwright")
    sys.exit(1)

try:
    from aiohttp import web
except ImportError:
    print("ERROR: aiohttp not installed")
    print("Install with: pip install aiohttp")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('solace-browser')

class SolaceBrowser:
    """
    Custom Solace Browser - Headless Chromium with CDP Protocol
    """

    def __init__(self, headless: bool = True, debug_ui: bool = False):
        self.headless = headless
        self.debug_ui = debug_ui
        self.browser: Optional[Browser] = None
        self.pages: Dict[str, Page] = {}
        self.current_page: Optional[Page] = None
        self.message_id_counter = 0
        self.event_history = []

    async def start(self):
        """Start the Solace Browser"""
        logger.info(f"Starting Solace Browser (headless={self.headless})")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        # Create initial page
        context = await self.browser.new_context()
        page = await context.new_page()
        page_id = str(uuid.uuid4())
        self.pages[page_id] = page
        self.current_page = page

        # Setup page events
        page.on('console', self._on_console)
        page.on('load', self._on_page_load)

        logger.info(f"✓ Solace Browser started (page_id={page_id})")
        return page_id

    async def stop(self):
        """Stop the Solace Browser"""
        if self.browser:
            await self.browser.close()
            logger.info("✓ Solace Browser stopped")

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Navigating to: {url}")
            response = await self.current_page.goto(url, wait_until='domcontentloaded')

            return {
                "success": True,
                "url": url,
                "status": response.status if response else None,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return {"error": str(e)}

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Clicking: {selector}")
            await self.current_page.click(selector)
            await asyncio.sleep(0.5)  # Wait for action to complete

            return {
                "success": True,
                "selector": selector,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return {"error": str(e)}

    async def fill(self, selector: str, text: str) -> Dict[str, Any]:
        """Fill a form field with text"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Filling {selector} with text")
            await self.current_page.fill(selector, text)
            await asyncio.sleep(0.3)

            return {
                "success": True,
                "selector": selector,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Fill failed: {e}")
            return {"error": str(e)}

    async def take_screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            if not filename:
                filename = f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"

            artifacts_dir = Path("artifacts")
            artifacts_dir.mkdir(exist_ok=True)
            filepath = artifacts_dir / filename

            logger.info(f"Taking screenshot: {filepath}")
            await self.current_page.screenshot(path=str(filepath))

            return {
                "success": True,
                "filename": filename,
                "filepath": str(filepath),
                "size": filepath.stat().st_size if filepath.exists() else 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"error": str(e)}

    async def get_snapshot(self) -> Dict[str, Any]:
        """Get page HTML snapshot"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("Getting page snapshot")
            html = await self.current_page.content()

            return {
                "success": True,
                "html_length": len(html),
                "url": self.current_page.url,
                "title": await self.current_page.title(),
                "html": html[:1000] + "..." if len(html) > 1000 else html,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")
            return {"error": str(e)}

    async def evaluate(self, expression: str) -> Dict[str, Any]:
        """Execute JavaScript in the page"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Evaluating: {expression[:50]}...")
            result = await self.current_page.evaluate(expression)

            return {
                "success": True,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Evaluate failed: {e}")
            return {"error": str(e)}

    def _on_console(self, msg):
        """Handle console messages"""
        logger.info(f"[CONSOLE] {msg.text}")
        self.event_history.append({
            "type": "console",
            "message": msg.text,
            "timestamp": datetime.now().isoformat()
        })

    def _on_page_load(self):
        """Handle page load events"""
        logger.info("Page loaded")
        self.event_history.append({
            "type": "pageload",
            "url": self.current_page.url if self.current_page else None,
            "timestamp": datetime.now().isoformat()
        })


class SolaceBrowserServer:
    """HTTP/WebSocket server for CDP protocol"""

    def __init__(self, browser: SolaceBrowser, port: int = 9222):
        self.browser = browser
        self.port = port
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/json/version', self._handle_version)
        self.app.router.add_get('/json/list', self._handle_list)
        self.app.router.add_post('/api/navigate', self._handle_navigate)
        self.app.router.add_post('/api/click', self._handle_click)
        self.app.router.add_post('/api/fill', self._handle_fill)
        self.app.router.add_post('/api/screenshot', self._handle_screenshot)
        self.app.router.add_post('/api/snapshot', self._handle_snapshot)
        self.app.router.add_post('/api/evaluate', self._handle_evaluate)
        self.app.router.add_get('/api/status', self._handle_status)
        self.app.router.add_get('/api/events', self._handle_events)

        # Debug UI routes
        if self.browser.debug_ui:
            self.app.router.add_get('/', self._handle_ui)
            self.app.router.add_static('/static', Path(__file__).parent / 'browser_ui')

    async def _handle_version(self, request):
        """Return browser version (CDP compatible)"""
        return web.json_response({
            "Browser": "Solace Browser/1.0.0",
            "Protocol-Version": "1.3",
            "User-Agent": "Solace/1.0.0",
            "V8-Version": "12.0.0"
        })

    async def _handle_list(self, request):
        """Return list of pages (CDP compatible)"""
        if not self.browser.current_page:
            return web.json_response([])

        return web.json_response([{
            "description": "Solace Browser Page",
            "devtoolsFrontendUrl": f"devtools://devtools/bundled/inspector.html",
            "faviconUrl": "",
            "id": str(id(self.browser.current_page)),
            "parentId": "",
            "title": await self.browser.current_page.title(),
            "type": "page",
            "url": self.browser.current_page.url,
            "webSocketDebuggerUrl": f"ws://localhost:{self.port}/ws"
        }])

    async def _handle_navigate(self, request):
        """Navigate to URL"""
        data = await request.json()
        result = await self.browser.navigate(data.get('url', ''))
        return web.json_response(result)

    async def _handle_click(self, request):
        """Click element"""
        data = await request.json()
        result = await self.browser.click(data.get('selector', ''))
        return web.json_response(result)

    async def _handle_fill(self, request):
        """Fill form field"""
        data = await request.json()
        result = await self.browser.fill(
            data.get('selector', ''),
            data.get('text', '')
        )
        return web.json_response(result)

    async def _handle_screenshot(self, request):
        """Take screenshot"""
        data = await request.json()
        result = await self.browser.take_screenshot(data.get('filename'))
        return web.json_response(result)

    async def _handle_snapshot(self, request):
        """Get page snapshot"""
        result = await self.browser.get_snapshot()
        return web.json_response(result)

    async def _handle_evaluate(self, request):
        """Evaluate JavaScript"""
        data = await request.json()
        result = await self.browser.evaluate(data.get('expression', ''))
        return web.json_response(result)

    async def _handle_status(self, request):
        """Get browser status"""
        return web.json_response({
            "running": self.browser.browser is not None,
            "headless": self.browser.headless,
            "current_url": self.browser.current_page.url if self.browser.current_page else None,
            "pages": len(self.browser.pages),
            "events": len(self.browser.event_history)
        })

    async def _handle_events(self, request):
        """Get event history"""
        limit = int(request.query.get('limit', 100))
        return web.json_response(self.browser.event_history[-limit:])

    async def _handle_ui(self, request):
        """Serve debugging UI"""
        return web.Response(text=self._get_ui_html(), content_type='text/html')

    def _get_ui_html(self):
        """Generate debugging UI HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Solace Browser - Debug UI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }
        .container { display: flex; height: 100vh; }
        .sidebar { width: 25%; background: #1e1e1e; color: #fff; padding: 20px; overflow-y: auto; border-right: 1px solid #333; }
        .main { width: 75%; display: flex; flex-direction: column; }
        .viewport { flex: 1; background: #fff; border: 1px solid #ddd; position: relative; overflow: auto; }
        .controls { padding: 20px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
        .input-group { margin-bottom: 10px; }
        input, button { padding: 8px 12px; margin-right: 10px; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #007bff; color: white; cursor: pointer; border: none; }
        button:hover { background: #0056b3; }
        .events { margin-top: 20px; }
        .event { background: #f0f0f0; padding: 10px; margin-bottom: 5px; border-left: 3px solid #007bff; font-size: 12px; }
        .status { padding: 10px; background: #e8f5e9; border-radius: 4px; margin-bottom: 10px; }
        h2 { margin: 20px 0 10px 0; font-size: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>Solace Browser</h1>
            <div class="status" id="status">Loading...</div>

            <h2>Controls</h2>
            <div class="input-group">
                <input type="text" id="urlInput" placeholder="Enter URL" style="width: 100%;">
                <button onclick="navigate()">Navigate</button>
            </div>

            <div class="input-group">
                <input type="text" id="selectorInput" placeholder="CSS Selector" style="width: 100%;">
                <button onclick="click()">Click</button>
            </div>

            <div class="input-group">
                <input type="text" id="textInput" placeholder="Text to fill" style="width: 100%;">
                <button onclick="fill()">Fill</button>
            </div>

            <button onclick="screenshot()" style="width: 100%; margin-bottom: 10px;">📸 Screenshot</button>
            <button onclick="snapshot()" style="width: 100%;">📄 Snapshot</button>

            <div class="events">
                <h2>Events</h2>
                <div id="eventsList"></div>
            </div>
        </div>

        <div class="main">
            <div class="controls">
                <h3>Viewport</h3>
                <p id="currentUrl">No page loaded</p>
            </div>
            <div class="viewport" id="viewport">
                <div style="padding: 20px; color: #999;">Loading browser...</div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = 'http://localhost:9222';

        async function navigate() {
            const url = document.getElementById('urlInput').value;
            const res = await fetch(`${API_BASE}/api/navigate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();
            console.log('Navigate:', data);
            updateStatus();
        }

        async function click() {
            const selector = document.getElementById('selectorInput').value;
            const res = await fetch(`${API_BASE}/api/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selector })
            });
            const data = await res.json();
            console.log('Click:', data);
        }

        async function fill() {
            const selector = document.getElementById('selectorInput').value;
            const text = document.getElementById('textInput').value;
            const res = await fetch(`${API_BASE}/api/fill`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selector, text })
            });
            const data = await res.json();
            console.log('Fill:', data);
        }

        async function screenshot() {
            const res = await fetch(`${API_BASE}/api/screenshot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();
            alert('Screenshot saved: ' + data.filename);
        }

        async function snapshot() {
            const res = await fetch(`${API_BASE}/api/snapshot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();
            alert('Snapshot: ' + data.url);
        }

        async function updateStatus() {
            const res = await fetch(`${API_BASE}/api/status`);
            const data = await res.json();
            document.getElementById('status').innerHTML = `
                <strong>Status:</strong> ${data.running ? '✓ Running' : '✗ Stopped'}<br>
                <strong>URL:</strong> ${data.current_url || 'None'}<br>
                <strong>Pages:</strong> ${data.pages}
            `;
            document.getElementById('currentUrl').textContent = `Current: ${data.current_url || 'None'}`;

            // Load events
            const evRes = await fetch(`${API_BASE}/api/events?limit=20`);
            const events = await evRes.json();
            const eventsList = document.getElementById('eventsList');
            eventsList.innerHTML = events.reverse().map(e => `
                <div class="event">
                    <strong>${e.type}</strong><br>
                    ${e.message || e.url || ''}<br>
                    <small>${new Date(e.timestamp).toLocaleTimeString()}</small>
                </div>
            `).join('');
        }

        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>
        """

    async def start(self):
        """Start the server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        logger.info(f"✓ CDP Server started on http://localhost:{self.port}")

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            await runner.cleanup()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Solace Browser - Custom Headless Browser')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run in headless mode (default: True)')
    parser.add_argument('--show-ui', action='store_true',
                       help='Show debugging UI (default: False)')
    parser.add_argument('--port', type=int, default=9222,
                       help='CDP server port (default: 9222)')

    args = parser.parse_args()

    # Create and start browser
    browser = SolaceBrowser(headless=args.headless, debug_ui=args.show_ui)
    await browser.start()

    # Create and start server
    server = SolaceBrowserServer(browser, port=args.port)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await browser.stop()


if __name__ == '__main__':
    asyncio.run(main())
