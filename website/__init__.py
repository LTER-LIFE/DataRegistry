#!/usr/bin/python
# Title: __init__.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
from flask import Flask, session, request, redirect
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from passlib.context import CryptContext
from dotenv import load_dotenv
import os
import psycopg2

# load env
load_dotenv()

print(os.environ.get('DB_POSTGRES_URI'))
# init db
db = SQLAlchemy()
DB_NAME = 'EcoMeta'
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
jwt = JWTManager()
migrate = Migrate()
# Init app
def create_app():
    app = Flask(__name__)
    # database & config (Turn into its own config + env files once done with project)
    app.config['SECRET_KEY'] = 'tmptmptmp'  #make sec in sep file
    postgres_uri = f'postgresql://tmp_user:ecotemp@localhost:5432/{DB_NAME}' # secret
    app.config['SQLALCHEMY_DATABASE_URI'] = postgres_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    JWT_SECRET_KEY = 'tempsecretkey'    # make secret in sep file
    JWT_TOKEN_LOCATION = ['headers']
    # request identity
    JWT_IDENTITY_CLAIM = 'user_id' # could be email # defaul == sub

    # init db
    db.init_app(app)
    migrate.init_app(app, db)
    # init jwt
    jwt.init_app(app)
    # Import blueprints
    from .routes import homepage
    # Register blueprints
    app.register_blueprint(homepage, url_prefix='/')

    # import the classes
    from .models import Catalog
    with app.app_context():
        db.create_all()

    create_database(app)

    return app

def create_database(app):
    if not os.path.exists(f'postgresql://tmp_user:ecotemp@localhost:5432/{DB_NAME}'):
        with app.app_context():
            db.create_all()
            print('Created The Database: {}'.format(DB_NAME))