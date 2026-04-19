"""Entry point for the RSSfedder Flask app.

Creates the Flask application, loads the SECRET_KEY, registers the `auth` and
`main` blueprints, initializes the SQLite database (schema + seed default
user/feeds), and starts the background periodic feed-fetch thread. The
WERKZEUG_RUN_MAIN guard prevents the fetch thread from being started twice
under Flask's debug reloader.
"""

import os
import warnings
from logging_config import configure_logging

configure_logging()

from flask import Flask
from db import init_db, seed_default_feeds, seed_default_user
from auth import auth_bp
from routes import main_bp
from feeds import start_periodic_fetch

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    warnings.warn("SECRET_KEY not set in .env -- using random key (sessions will not persist across restarts)")
    app.secret_key = os.urandom(24).hex()

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

# Initialize database on startup
init_db()
seed_default_user()
seed_default_feeds()

if __name__ == "__main__":
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes')
    if not debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_periodic_fetch()
    app.run(debug=debug)
