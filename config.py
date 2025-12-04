import base64
import hashlib
import json
import os
import re
from os import environ, urandom

import requests


def get_well_known_config(url):
    result = requests.get(url)
    if result.status_code == 200:
        return json.loads(result.content)
    return {}


def get_code_challenge():
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
    code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)
    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
    code_challenge = code_challenge.replace('=', '')
    return code_verifier, code_challenge


class Config(object):
    SECRET_KEY = environ.get('SECRET_KEY') or urandom(24)
    SESSION_TYPE = environ.get('SESSION_TYPE', "filesystem")
    PROXY_PREFIX = environ.get('PROXY_PREFIX') or "/"
    SESSION_COOKIE_SAMESITE = environ.get("SESSION_COOKIE_SAMESITE", "None")

    # Database
    DB_USER = environ.get("DB_USER")
    DB_PWD = environ.get("DB_PWD")
    DB_HOST = environ.get("DB_HOST")
    DB_NAME = environ.get("DB_NAME")
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PWD}@{DB_HOST}/{DB_NAME}"
    SPATIALITE_LIBRARY_PATH = environ.get('SPATIALITE_LIBRARY_PATH') or 'la'

    ## Surf settings
    SURF_CLIENT_ID = environ.get("SURF_CLIENT_ID", "None")
    SURF_CLIENT_SECRET = environ.get("SURF_CLIENT_SECRET", "None")
    SURF_DOTWELLKNOWN_CONFIG = get_well_known_config(environ.get("SURF_DOTWELLKNOWN", "None"))
    SURF_REDIRECT_URI = environ.get("SURF_REDIRECT_URI", "None")
    SURF_SRAM_GROUP_PREFIX = environ.get("SURF_SRAM_GROUP_PREFIX")
    SURF_SRAM_GROUP_POSTFIX = environ.get("SURF_SRAM_GROUP_POSTFIX")
    SURF_EDITOR_GROUP = f"{SURF_SRAM_GROUP_PREFIX}{SURF_SRAM_GROUP_POSTFIX}"

    CODE_VERIFIER, CODE_CHALLENGE = get_code_challenge()

    ## Elastic settings
    ELASTIC_HOST = environ.get("ELASTIC_HOST")
    ELASTIC_CA_CERT = environ.get("ELASTIC_CA_CERT", "/app/certs/ca/ca.crt")
    ELASTIC_USER = environ.get("ELASTIC_USER")
    ELASTIC_PASSWORD = environ.get("ELASTIC_PASSWORD")
    ELASTIC_VERIFY_CERTS = environ.get("ELASTIC_VERIFY_CERTS", True)
    ELASTIC_INDEX_NAME = environ.get("ELASTIC_INDEX_NAME", "dataset")
