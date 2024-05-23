#!/usr/bin/python
# Title: __init__.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
from flask import Flask, session, request, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from os import path
import psycopg2

# init db
db = SQLAlchemy()
DB_NAME = 'EcoMeta'

# Init app
def create_app():
    app = Flask(__name__)
    # database
    app.config['SECRET_KEY'] = 'tmptmptmp'
    postgres_uri = f'postgresql://tmp_user:ecotemp@localhost:5432/{DB_NAME}'
    app.config['SQLALCHEMY_DATABASE_URI'] = postgres_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # init db
    db.init_app(app)
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
    if not path.exists(f'postgresql://tmp_user:ecotemp@localhost:5432/{DB_NAME}'):
        with app.app_context():
            db.create_all()
            print('Created The Database: {}'.format(DB_NAME))