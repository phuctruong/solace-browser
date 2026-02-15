#!/usr/bin/env python3

"""
Persistent Browser Server - Stays alive, allows reconnection
Based on OpenClaw pattern but simpler (HTTP only, no WebSockets needed)

CONSOLIDATED: Uses browser module instead of individual files
- browser_interactions.py -> browser.core
- enhanced_browser_interactions.py -> browser.advanced
- HTTP handlers -> browser.handlers
"""

import asyncio
import signal
import logging
import argparse

from browser.http_server import PersistentBrowserServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('browser-server')


# ============================================================================
# Main entry point
# ============================================================================

async def main(headless=False):
    server = PersistentBrowserServer(port=9222, headless=headless)

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("\nShutting down...")
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
    parser = argparse.ArgumentParser(description='Persistent Browser Server for Cloud Run')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode (for Cloud Run deployment)')
    args = parser.parse_args()

    print(f"Starting browser server ({'HEADLESS' if args.headless else 'HEADED'} mode)")
    asyncio.run(main(headless=args.headless))
