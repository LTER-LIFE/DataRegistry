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

_REVIEWABLE_SYNC_QUEUE = "reviewable_sync_keys"
_REVIEWABLE_OWNER_CONFIG = {
    "dataset": ("dataset", "dataset_id"),
}


def _lifecycle_owner(lifecycle):
    config = _REVIEWABLE_OWNER_CONFIG.get(lifecycle.owner_type)
    return getattr(lifecycle, config[0], None) if config else None


def _reviewable_identity(record):
    owner_type = getattr(record, "review_owner_kind", None)
    config = _REVIEWABLE_OWNER_CONFIG.get(owner_type)
    if not config:
        return None
    owner_id = getattr(record, config[1], None)
    return (owner_type, owner_id) if owner_id is not None else None


def _lifecycle_owner_identity(lifecycle):
    owner = _lifecycle_owner(lifecycle)
    return _reviewable_identity(owner) if owner is not None else None


def _queue_reviewable(session, identity):
    if identity is not None:
        session.info.setdefault(_REVIEWABLE_SYNC_QUEUE, set()).add(identity)


def validate_db(app):
    """Register scoped-session cleanup with the Flask application."""

    @app.teardown_appcontext
    def remove_session(exception=None):
        db_session.remove()


@event.listens_for(db_session, "before_flush")
def prepare_reviewable_changes(session, flush_context, instances):
    """Update owner timestamps and capture identities before lifecycle cascades."""
    from application.models import Dataset, ReviewLifecycle

    for obj in list(session.dirty):
        if isinstance(obj, Dataset):
            state = inspect(obj)
            if (
                session.is_modified(obj, include_collections=True)
                and not state.attrs.modified.history.has_changes()
            ):
                obj.modified = datetime.utcnow()
        elif isinstance(obj, ReviewLifecycle) and session.is_modified(
            obj, include_collections=False
        ):
            owner = _lifecycle_owner(obj)
            if owner is not None and owner not in session.deleted:
                state = inspect(owner)
                if not state.attrs.modified.history.has_changes():
                    owner.modified = datetime.utcnow()

    # Capture lifecycle ownership while the relationship still exists. Deleting a
    # lifecycle cascades its dataset in PostgreSQL, so resolving it after flush
    # would be too late to know which Elasticsearch document must be removed.
    for obj in session.new.union(session.dirty).union(session.deleted):
        if isinstance(obj, Dataset):
            _queue_reviewable(session, _reviewable_identity(obj))
        elif isinstance(obj, ReviewLifecycle):
            _queue_reviewable(session, _lifecycle_owner_identity(obj))


@event.listens_for(db_session, "after_flush")
def queue_reviewable_sync(session, flush_context):
    """Capture identities assigned during flush without contacting search."""
    from application.models import Dataset, ReviewLifecycle

    # New owners have their primary keys only after flush. The queue is a set, so
    # this second pass safely deduplicates identities captured before the cascade.
    for obj in session.new.union(session.dirty).union(session.deleted):
        if isinstance(obj, Dataset):
            _queue_reviewable(session, _reviewable_identity(obj))
        elif isinstance(obj, ReviewLifecycle):
            _queue_reviewable(session, _lifecycle_owner_identity(obj))


@event.listens_for(db_session, "after_commit")
def sync_reviewables_after_commit(session):
    """Synchronize committed owners; public reads remain fail-closed on errors."""
    identities = session.info.pop(_REVIEWABLE_SYNC_QUEUE, set())
    if not identities or isinstance(session.get_bind(), Connection):
        return

    from application.models import Dataset, REVIEW_OWNER_DATASET, REVIEW_STATUS_ACCEPTED

    sync_session = sessionmaker(bind=session.get_bind())()
    try:
        for owner_type, owner_id in sorted(identities):
            try:
                if owner_type != REVIEW_OWNER_DATASET:
                    logging.error(
                        "No search synchronization handler for %s %s",
                        owner_type,
                        owner_id,
                    )
                    continue

                dataset = sync_session.get(Dataset, owner_id)
                if (
                    dataset is not None
                    and dataset.review_lifecycle.status == REVIEW_STATUS_ACCEPTED
                ):
                    index_document_data(owner_id, dataset.to_dict())
                else:
                    delete_document_id(owner_id)
            except Exception:
                logging.exception(
                    "Failed to synchronize %s %s",
                    owner_type,
                    owner_id,
                )
    finally:
        sync_session.close()


@event.listens_for(db_session, "after_rollback")
def discard_reviewable_sync(session):
    session.info.pop(_REVIEWABLE_SYNC_QUEUE, None)
