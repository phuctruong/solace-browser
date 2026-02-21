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
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--port', type=int, default=9222)
    parser.add_argument('--session-file', default=None)
    parser.add_argument('--user-data-dir', default=None)
    # Default autosave disabled: background storage_state calls can disrupt interactive typing.
    parser.add_argument('--autosave-seconds', type=int, default=0)
    args, _unknown = parser.parse_known_args()

    server = PersistentBrowserServer(
        port=args.port,
        headless=headless,
        session_file=args.session_file,
        autosave_seconds=args.autosave_seconds,
        user_data_dir=args.user_data_dir,
    )

    shutdown = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_shutdown():
        logger.info("\nShutting down...")
        shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            # Fallback for platforms without add_signal_handler support.
            signal.signal(sig, lambda *_: _request_shutdown())

    await server.start()

    try:
        await shutdown.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Persistent Browser Server for Cloud Run')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode (for Cloud Run deployment)')
    parser.add_argument('--port', type=int, default=9222,
                       help='HTTP port (default: 9222)')
    parser.add_argument('--session-file', default=None,
                       help='Playwright storage_state JSON file to load/save (default: $SOLACE_SESSION_FILE or artifacts/solace_session.json)')
    parser.add_argument('--user-data-dir', default=None,
                       help='Chrome user data dir for a persistent profile (default: $SOLACE_USER_DATA_DIR). If set, login sessions persist automatically across restarts.')
    parser.add_argument('--autosave-seconds', type=int, default=0,
                       help='Autosave storage_state every N seconds (default: 0 disables; can be disruptive while typing)')
    args = parser.parse_args()

    print(f"Starting browser server ({'HEADLESS' if args.headless else 'HEADED'} mode)")
    asyncio.run(main(headless=args.headless))
