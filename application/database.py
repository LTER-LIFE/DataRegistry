from geoalchemy2 import load_spatialite
from sqlalchemy import create_engine, event
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy_utils import database_exists

from application.search_index import index_document, delete_document
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
        Base.metadata.create_all(bind=engine) # Create new DB
        print(f"Database Created {engine.url}")  # Verifies if database is there or not.
    else:
        print(f"Database {engine.url} Already Exists")

    @app.teardown_appcontext
    def remove_session(exception=None):
        """
        Register teardown to clean up session
        """
        db_session.remove()

@event.listens_for(db_session, "after_flush")
def after_flush(session, flush_context):
    """
    SQLAlchemy event hook that runs after each session flush.

    This hook is responsible for syncing any SQLAlchemy model instances
    that define a `to_dict()` method with the Elasticsearch index.

    It handles:
    - Newly created objects (`session.new`)
    - Updated objects (`session.dirty`)
    - Deleted objects (`session.deleted`)

    Models are identified as indexable if they implement a `to_dict()` method.
    This avoids the need for a mixin or marker class.

    Assumes the existence of two functions:
    - `index_document(obj: Any)` – adds or updates a document in Elasticsearch
    - `delete_document(obj: Any)` – removes a document from Elasticsearch

    This should be registered once, typically in `database.py` after the Session class is defined.
    """

    for obj in session.new.union(session.dirty):
        if obj.__class__.__name__ is "Dataset":
            index_document(obj)

    for obj in session.deleted:
        if obj.__class__.__name__ is "Dataset":
            delete_document(obj)