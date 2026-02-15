#!/bin/bash

# Start Solace Browser Server - Keeps running in background
# You can disconnect and reconnect to it

echo "🚀 Starting Solace Browser Server..."
echo ""
echo "The browser will stay open even after disconnection"
echo "You can reconnect anytime to continue where you left off"
echo ""

# Start the server in background
python3 -c "
import asyncio
from solace_browser_server import SolaceBrowser

async def main():
    browser = SolaceBrowser(headless=False, debug_ui=False)
    await browser.start()

    print('')
    print('='*80)
    print('✅ SOLACE BROWSER SERVER RUNNING')
    print('='*80)
    print('')
    print('Browser is now running and waiting for commands')
    print('HTTP Server: http://localhost:9222')
    print('')
    print('Available endpoints:')
    print('  GET  /api/aria-snapshot      - Get ARIA tree')
    print('  GET  /api/dom-snapshot       - Get DOM tree')
    print('  GET  /api/page-snapshot      - Get combined snapshot')
    print('  POST /api/act                - Execute action')
    print('  POST /api/navigate           - Navigate to URL')
    print('')
    print('Press Ctrl+C to stop the server')
    print('='*80)
    print('')

    # Keep server running
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
" &

SERVER_PID=$!
echo "Server PID: $SERVER_PID"
echo ""
echo "To stop the server later:"
echo "  kill $SERVER_PID"
echo ""

# Wait a bit for server to start
sleep 3

echo "✅ Server should be running now"
echo ""
echo "Test it:"
echo "  curl http://localhost:9222/api/page-snapshot"
echo ""
