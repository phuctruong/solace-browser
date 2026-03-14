# Diagram: 05-solace-runtime-architecture
"""
yinyang-server.py — Entry point shim for Yinyang Server.
Run as: python yinyang-server.py [repo_root]

The importable module lives in yinyang_server.py (underscore).
Python cannot import modules with hyphens, so tests import yinyang_server.
This file is the CLI entry point only.
"""
import sys

# Allow running from project root without installing.
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from yinyang_server import start_server

if __name__ == "__main__":
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    start_server(8888, repo_root)
