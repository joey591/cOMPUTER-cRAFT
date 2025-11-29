"""Main Flask application."""
import os
from pathlib import Path
from flask import Flask
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


@app.before_request
def before_request():
    """Handle before request."""
    pass


@app.teardown_appcontext
def teardown_appcontext(error):
    """Cleanup on app context teardown."""
    pass


if __name__ == '__main__':
    from config import SERVER_HOST, SERVER_PORT
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)

