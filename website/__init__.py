## DONE


#!/usr/bin/python
# Title: __init__.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
import os
from .models.models import Catalog
from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from passlib.context import CryptContext

# load env
load_dotenv()

print(os.environ.get('DB_POSTGRES_URI'))
# init db
# db = SQLAlchemy()
# DB_NAME = 'EcoMeta'
db = SQLAlchemy()
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
jwt = JWTManager()
ma = Marshmallow()
# Init app
def create_app():
    app = Flask(__name__)
    # database & config (Turn into its own config + env files once done with project)
    app.config.from_object("config")
    # postgres_uri = f'postgresql://tmp_user:ecotemp@localhost:5432/{DB_NAME}' # secret
    # app.config['SQLALCHEMY_DATABASE_URI'] = postgres_uri
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    # init db
    db.init_app(app)

    # init jwt
    jwt.init_app(app)
    # Import blueprints
    from .routes import homepage
    # Register blueprints
    app.register_blueprint(homepage, url_prefix='/')

    # import the classes
    with app.app_context():
        db.create_all()

    create_database(app)

    return app

def create_database(app):
    if not os.path.exists(app.config['SQLALCHEMY_DATABASE_URI']):
        with app.app_context():
            db.create_all()
