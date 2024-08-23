import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

FLASK_DEBUG = os.environ.get('FLASK_DEBUG')
PROXY_PREFIX =  os.environ.get('PROXY_PREFIX') or "/"
SECRET_KEY = os.environ.get('APP_SECRET_KEY')
ENV = os.environ.get('ENV')
SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
SQLALCHEMY_TRACK_MODIFICATIONS = False
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_TOKEN_LOCATION = ['headers']
JWT_IDENTITY_CLAIM = 'user_id'  # default ==sub
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=20)

