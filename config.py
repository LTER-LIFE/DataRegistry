from os import environ, path, urandom
import socket

from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
if socket.gethostname() == "NIOO0035":
    load_dotenv(path.join(basedir, "config/ecosearch_test.conf"))
else:
    load_dotenv(path.join(basedir, "config/ecosearch_local.conf"))


class Config(object):
    SERVER_NAME = environ.get('SERVER_NAME') or "localhost:5000"
    SECRET_KEY = environ.get('SECRET_KEY') or urandom(24)
    SESSION_TYPE = environ.get('SESSION_TYPE')
    PROXY_PREFIX = environ.get('PROXY_PREFIX') or "/"

    SESSION_COOKIE_SAMESITE = environ.get("SESSION_COOKIE_SAMESITE", "None")
    SQLALCHEMY_DATABASE_URI = environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///localapp.db'
    SPATIALITE_LIBRARY_PATH = environ.get('SPATIALITE_LIBRARY_PATH') or 'la'
