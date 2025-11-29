"""Configuration settings for the Flask application."""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Database configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'data' / 'transporter.db'))
DATABASE_DIR = os.path.dirname(DATABASE_PATH)
os.makedirs(DATABASE_DIR, exist_ok=True)

# Flask configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
FORCE_HTTPS = os.getenv('FORCE_HTTPS', 'True').lower() == 'true'  # Default to True for production

# API configuration
API_KEY_LENGTH = 32
API_KEY_PREFIX = 'cc_'

# Background job configuration
PERIPHERAL_DISCOVERY_INTERVAL = 30  # seconds
MACHINE_TIMEOUT = 60  # seconds before marking machine as offline

# Server configuration
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', 7781))

# Item filtering
FUZZY_MATCH_THRESHOLD = 0.6  # Minimum similarity score (0-1)
ABBREVIATION_MAP = {
    'b': 'block',
    'i': 'ingot',
    'n': 'nugget',
    'g': 'gem',
    'd': 'dust',
    'p': 'plate',
}

