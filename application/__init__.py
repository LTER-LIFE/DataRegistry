from os import environ

from flask import Flask, session
from werkzeug.middleware.proxy_fix import ProxyFix

from application.database import validate_db
from config import Config
from flask_login import LoginManager
from flask_session import Session
from flask_jwt_extended import JWTManager

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(encoding='utf-8', level=logging.DEBUG)


def create_app():
    """
    Create app is ran to fire up the flask application.

    :return: Flask application object
    """
    proxy_prefix = environ.get('PROXY_PREFIX')
    url_prefix = f"/{proxy_prefix}/".rstrip("/") if proxy_prefix else ""

    app = Flask(__name__, static_url_path=f'{url_prefix}/')

    # Configure the flask app instance
    app.config.from_object(Config)

    app.secret_key = app.config.get("SECRET_KEY")
    Session(app)

    # Tell flask its behind a proxy
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # Register blueprints
    with app.app_context():
        login_manager = LoginManager()
        login_manager.login_view = 'main_bp.login'
        app.login_manager = login_manager

        from application import routes

        app.register_blueprint(blueprint=routes.main_bp, url_prefix=url_prefix)
        app.jwt = JWTManager(app)

        validate_db()

    return app
