"""Lifecycle transitions for canonical dataset records."""

from datetime import datetime

from application.models import (
    DATASET_STATUS_ACCEPTED,
    DATASET_STATUS_REJECTED,
    DATASET_STATUS_REVISION,
    DATASET_STATUS_SUBMITTED,
)


ALLOWED_TRANSITIONS = {
    DATASET_STATUS_SUBMITTED: {
        DATASET_STATUS_REVISION,
        DATASET_STATUS_REJECTED,
        DATASET_STATUS_ACCEPTED,
    },
    DATASET_STATUS_REVISION: {
        DATASET_STATUS_SUBMITTED,
        DATASET_STATUS_REJECTED,
    },
    DATASET_STATUS_REJECTED: {DATASET_STATUS_REVISION},
    DATASET_STATUS_ACCEPTED: {DATASET_STATUS_REVISION},
}


def transition_dataset(dataset, target_status, review_comment=None, changed_at=None):
    """Apply one valid lifecycle transition without committing the session."""
    if target_status not in ALLOWED_TRANSITIONS.get(dataset.status, set()):
        raise ValueError(
            f"Cannot transition dataset from {dataset.status!r} to {target_status!r}."
        )

    comment = review_comment.strip() if review_comment else None
    if target_status in {DATASET_STATUS_REVISION, DATASET_STATUS_REJECTED} and not comment:
        raise ValueError("Revision and rejection require review feedback.")

    changed_at = changed_at or datetime.utcnow()
    dataset.status = target_status
    dataset.modified = changed_at

    if target_status == DATASET_STATUS_ACCEPTED:
        dataset.accepted_at = changed_at
        dataset.review_comment = None
    elif target_status in {DATASET_STATUS_REVISION, DATASET_STATUS_REJECTED}:
        dataset.review_comment = comment

    return dataset
