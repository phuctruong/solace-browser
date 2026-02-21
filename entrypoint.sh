#!/bin/bash
# Entrypoint for Cloud Run deployment

# Set environment
export PYTHONUNBUFFERED=1
export PORT=8080

# Start the Python server with a simple HTTP endpoint
python3 -c "
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': '2.0.0', 'mode': 'phase2'})

@app.route('/status')
def status():
    return jsonify({
        'service': 'solace-browser',
        'phase': 'phase2-mvp',
        'status': 'online',
        'features': ['google-search', 'multi-platform-crawl', 'headless-automation'],
        'port': 8080
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
" &

# Also start the actual browser server in background if needed
python3 /app/solace_browser_server.py &

# Wait for services
wait
