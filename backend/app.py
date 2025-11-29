"""Main Flask application."""
import os
from pathlib import Path
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from config import SECRET_KEY, DEBUG

# Get base directory
BASE_DIR = Path(__file__).parent.parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'frontend' / 'templates'),
    static_folder=str(BASE_DIR / 'frontend' / 'static')
)
app.secret_key = SECRET_KEY
app.debug = DEBUG

# Handle reverse proxy (if needed)
# Trust X-Forwarded-* headers from proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # Number of proxies to trust
    x_proto=1,    # Trust X-Forwarded-Proto header
    x_host=1,     # Trust X-Forwarded-Host header
    x_port=1      # Trust X-Forwarded-Port header
)

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

