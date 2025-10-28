import base64
import hashlib
import json
import os
import re
import socket
from os import environ, path, urandom

import requests
from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
if socket.gethostname() == "nioo0061":
    load_dotenv(path.join(basedir, "config/ecosearch_test.conf"))
else:
    load_dotenv(path.join(basedir, "config/ecosearch_local.conf"))


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
    SERVER_NAME = environ.get('SERVER_NAME') or "localhost:5000"
    SECRET_KEY = environ.get('SECRET_KEY') or urandom(24)
    SESSION_TYPE = environ.get('SESSION_TYPE')
    PROXY_PREFIX = environ.get('PROXY_PREFIX') or "/"

    SESSION_COOKIE_SAMESITE = environ.get("SESSION_COOKIE_SAMESITE", "None")
    SQLALCHEMY_DATABASE_URI = environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///localapp.db'
    SPATIALITE_LIBRARY_PATH = environ.get('SPATIALITE_LIBRARY_PATH') or 'la'

    ## Surf settings
    SURF_CLIENT_ID = environ.get("SURF_CLIENT_ID", "None")
    SURF_CLIENT_SECRET = environ.get("SURF_CLIENT_SECRET", "None")
    SURF_DOTWELLKNOWN_CONFIG = get_well_known_config(environ.get("SURF_DOTWELLKNOWN", "None"))
    SURF_REDIRECT_URI = environ.get("SURF_REDIRECT_URI", "None")
    SURF_SRAM_GROUP_PREFIX = environ.get("SURF_SRAM_GROUP_PREFIX", "urn:mace:surf.nl:sram:group:")
    SURF_SRAM_GROUP_POSTFIX = environ.get("SURF_SRAM_GROUP_POSTFIX", "knaw:datamanagement:knawopenidtestap-ll_editor")
    SURF_EDITOR_GROUP = f"{SURF_SRAM_GROUP_PREFIX}{SURF_SRAM_GROUP_POSTFIX}"

    CODE_VERIFIER, CODE_CHALLENGE = get_code_challenge()

    ## Elastic settings
    ELASTIC_HOST = environ.get("ELASTIC_HOST", "https://localhost:9200/")
    ELASTIC_CA_CERT = environ.get("ELASTIC_CA_CERT", None)
    ELASTIC_USER = environ.get("ELASTIC_USER", "elastic")
    ELASTIC_PASSWORD = environ.get("ELASTIC_PASSWORD", "wqv-7S75rA3tMKra7qvT")
    ELASTIC_VERIFY_CERTS = environ.get("ELASTIC_VERIFY_CERTS", False)
    ELASTIC_INDEX_NAME = environ.get("ELASTIC_INDEX_NAME", "dataset")
