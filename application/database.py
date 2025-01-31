from geoalchemy2 import load_spatialite
from sqlalchemy import create_engine
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy_utils import database_exists
from config import Config

if Config.SQLALCHEMY_DATABASE_URI.find("sqlite") > -1:
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

print(Config.SQLALCHEMY_DATABASE_URI)
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI,
                       echo=True, connect_args=connect_args)

if Config.SQLALCHEMY_DATABASE_URI.find("sqlite") > -1:
    listen(engine, "connect", load_spatialite)
else:
    connect_args = {}

db_session = scoped_session(sessionmaker(autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def validate_db():
    """
    Create database if not excist, does not work very well
    """
    if not database_exists(engine.url):
        Base.metadata.create_all(bind=engine) # Create new DB
        print(f"Database Created {engine.url}")  # Verifies if database is there or not.
    else:
        print(f"Database {engine.url} Already Exists")








