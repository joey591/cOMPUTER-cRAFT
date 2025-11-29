#!/usr/bin/env python3
"""Entry point for the Flask application."""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

from app import app

if __name__ == '__main__':
    from config import SERVER_HOST, SERVER_PORT, DEBUG
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)

