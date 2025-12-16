from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database

from application.models import metadata
from config import Config

DB_NAME = 'ecosearchengine_test'

SQLALCHEMY_DATABASE_URI = f"postgresql://{Config.DB_USER}:{Config.DB_PWD}@{Config.DB_HOST}/{DB_NAME}"
engine = create_engine(SQLALCHEMY_DATABASE_URI)

def init_db():
    if not database_exists(engine.url):
        create_database(engine.url)

        with engine.connect() as con:
            con.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            con.commit()

    metadata.create_all(engine)


def remove_tables():
    metadata.drop_all(engine)