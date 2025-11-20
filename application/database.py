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

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI,
                       echo=True, connect_args=connect_args, pool_pre_ping=True)

if Config.SQLALCHEMY_DATABASE_URI.find("sqlite") > -1:
    listen(engine, "connect", load_spatialite)
else:
    connect_args = {}

db_session = scoped_session(sessionmaker(autoflush=True,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def validate_db(app):
    """
    Create database if not exist,

    Initialize the SQLAlchemy session and register teardown logic with the Flask app.

    This function sets up a scoped SQLAlchemy session and ensures that the session is properly
    removed at the end of each Flask application context. This helps prevent issues with
    dangling or invalid sessions, especially after failed transactions.

    Parameters:
        app (Flask): The Flask application instance.
    """
    if not database_exists(engine.url):
        
        print(f"Database Created {engine.url}")  # Verifies if database is there or not.
    else:
        print(f"Database {engine.url} Already Exists")

    Base.metadata.create_all(bind=engine) # Create new DB

    @app.teardown_appcontext
    def remove_session(exception=None):
        """
        Register teardown to clean up session
        """
        db_session.remove()





