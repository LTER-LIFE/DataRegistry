# fix for circular import issues with db
import flask_marshmallow
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from passlib.context import CryptContext

# Init the DB
db = SQLAlchemy()
ma = flask_marshmallow.Marshmallow()
# Encryption for passwords
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
# get the JWT manager
jwt = JWTManager()
# Init migrate & marshmallow
migrate = Migrate()
