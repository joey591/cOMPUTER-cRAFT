"""Main Flask application."""
import os
from pathlib import Path
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix
from config import SECRET_KEY, DEBUG, FORCE_HTTPS

# Get base directory
BASE_DIR = Path(__file__).parent.parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'frontend' / 'templates'),
    static_folder=str(BASE_DIR / 'frontend' / 'static')
)
app.secret_key = SECRET_KEY
app.debug = DEBUG

# Handle reverse proxy (for HTTPS behind proxy)
# Trust X-Forwarded-* headers from proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # Number of proxies to trust
    x_proto=1,    # Trust X-Forwarded-Proto header
    x_host=1,     # Trust X-Forwarded-Host header
    x_port=1      # Trust X-Forwarded-Port header
)

# Force HTTPS URLs when behind proxy
if FORCE_HTTPS:
    @app.before_request
    def force_https():
        if request.headers.get('X-Forwarded-Proto') == 'https':
            request.scheme = 'https'

from routes import api, web
from peripheral_discovery import PeripheralDiscovery

# Register blueprints
app.register_blueprint(api)
app.register_blueprint(web)

# Initialize database
from models import Database
db = Database()

# Initialize peripheral discovery
discovery = PeripheralDiscovery(app)
discovery.start()


@app.teardown_appcontext
def teardown_appcontext(error):
    """Cleanup on app context teardown."""
    pass


if __name__ == '__main__':
    from config import SERVER_HOST, SERVER_PORT
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)

