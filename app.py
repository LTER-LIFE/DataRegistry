# Fixed

# Title: app.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from dotenv import load_dotenv

from passlib.context import CryptContext
from auth.views import auth_blueprint
from website.views import homepage
from extensions import db, migrate, jwt
# Load the env
load_dotenv()
# Temp check if the environment is loaded
print(os.environ.get('DB_POSTGRES_URI'))


# Create the app function


def create_app():
    """

    :return:
    """
    # Set up app
    app = Flask(__name__)
    # Get configuration from Config
    app.config.from_object("config")

    # Init the db with the app
    db.init_app(app)

    migrate.init_app(app, db)
    # Init the JWT with the app
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(blueprint=homepage, url_prefix='/')
    app.register_blueprint(blueprint=auth_blueprint, url_prefix='/auth')

    # app.register_blueprint(blueprint=)
    return app


app = create_app()

#
# def create_database(app):
#     if not os.path.exists(app.config['SQLALCHEMY_DATABASE_URI']):
#         with app.app_context():
#             db.create_all()
#

# Create the flask app instance
if __name__ == '__main__':
    app.run(debug=True)
