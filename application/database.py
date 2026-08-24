import logging
from datetime import datetime

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from application.search_index import delete_document_id, index_document_data
from config import Config


engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    echo=True,
    pool_pre_ping=True,
)
db_session = scoped_session(sessionmaker(autoflush=True, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def validate_db(app):
    """Register scoped-session cleanup with the Flask application."""

    @app.teardown_appcontext
    def remove_session(exception=None):
        db_session.remove()


@event.listens_for(db_session, "before_flush")
def update_dataset_modified(session, flush_context, instances):
    """Keep the canonical last-change timestamp current for all ORM edits."""
    for obj in session.dirty:
        if obj.__class__.__name__ != "Dataset":
            continue
        state = inspect(obj)
        if session.is_modified(obj, include_collections=True) and not state.attrs.modified.history.has_changes():
            obj.modified = datetime.utcnow()


@event.listens_for(db_session, "after_flush")
def queue_dataset_sync(session, flush_context):
    """Capture changed IDs without contacting Elasticsearch pre-commit."""
    queued_ids = session.info.setdefault("dataset_sync_ids", set())
    for obj in session.new.union(session.dirty).union(session.deleted):
        if obj.__class__.__name__ == "Dataset" and obj.dataset_id is not None:
            queued_ids.add(obj.dataset_id)


@event.listens_for(db_session, "after_commit")
def sync_datasets_after_commit(session):
    """Synchronize committed changes; public reads remain fail-closed on errors."""
    dataset_ids = session.info.pop("dataset_sync_ids", set())
    if not dataset_ids or isinstance(session.get_bind(), Connection):
        return

    from application.models import DATASET_STATUS_ACCEPTED, Dataset

    sync_session = sessionmaker(bind=engine)()
    try:
        for dataset_id in dataset_ids:
            try:
                dataset = sync_session.get(Dataset, dataset_id)
                if dataset and dataset.status == DATASET_STATUS_ACCEPTED:
                    index_document_data(dataset_id, dataset.to_dict())
                else:
                    delete_document_id(dataset_id)
            except Exception:
                logging.exception("Failed to synchronize dataset %s", dataset_id)
    finally:
        sync_session.close()


@event.listens_for(db_session, "after_rollback")
def discard_dataset_sync(session):
    session.info.pop("dataset_sync_ids", None)
