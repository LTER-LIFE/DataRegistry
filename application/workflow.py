"""Shared lifecycle initialization and transitions for reviewable records."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import object_session

from application.models import (
    REVIEW_ACTOR_AUTHENTICATED,
    REVIEW_ACTOR_MODES,
    REVIEW_STATUS_ACCEPTED,
    REVIEW_STATUS_REJECTED,
    REVIEW_STATUS_REVISION,
    REVIEW_STATUS_SUBMITTED,
    ReviewLifecycle,
    ReviewTransition,
)


ALLOWED_TRANSITIONS = {
    REVIEW_STATUS_SUBMITTED: {
        REVIEW_STATUS_REVISION,
        REVIEW_STATUS_REJECTED,
        REVIEW_STATUS_ACCEPTED,
    },
    REVIEW_STATUS_REVISION: {
        REVIEW_STATUS_SUBMITTED,
        REVIEW_STATUS_REJECTED,
    },
    REVIEW_STATUS_REJECTED: {REVIEW_STATUS_REVISION},
    REVIEW_STATUS_ACCEPTED: {REVIEW_STATUS_REVISION},
}


def _actor(actor_id, actor_mode):
    if actor_mode not in REVIEW_ACTOR_MODES:
        raise ValueError(f"Unsupported review actor mode {actor_mode!r}.")

    normalized_actor_id = actor_id.strip() if actor_id else None
    if actor_mode == REVIEW_ACTOR_AUTHENTICATED and not normalized_actor_id:
        raise ValueError("Authenticated review activity requires an actor identity.")
    if actor_mode != REVIEW_ACTOR_AUTHENTICATED and normalized_actor_id:
        raise ValueError(
            f"Review actor mode {actor_mode!r} cannot include an actor identity."
        )
    return normalized_actor_id


def _current_lifecycle(record):
    lifecycle = getattr(record, "review_lifecycle", None)
    if lifecycle is None:
        raise ValueError("Reviewable record does not have a lifecycle.")
    if lifecycle.review_lifecycle_id is None:
        return lifecycle

    session = object_session(record)
    if session is None:
        raise ValueError("Persisted reviewable record is not attached to a session.")
    return session.execute(
        select(ReviewLifecycle)
        .where(
            ReviewLifecycle.review_lifecycle_id
            == lifecycle.review_lifecycle_id
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()


def initialize_reviewable(
    record,
    submitter_id=None,
    actor_id=None,
    actor_mode="anonymous",
    changed_at=None,
):
    """Attach a submitted lifecycle and initial event without committing."""
    if (
        getattr(record, "review_lifecycle", None) is not None
        or getattr(record, "review_lifecycle_id", None) is not None
    ):
        raise ValueError("Reviewable record already has a lifecycle.")
    if not hasattr(record, "review_owner_kind"):
        raise ValueError("Reviewable record does not declare an owner type.")
    if not hasattr(record, "modified"):
        raise ValueError("Reviewable record does not declare a modified timestamp.")

    actor_id = _actor(actor_id, actor_mode)
    submitter_id = submitter_id.strip() if submitter_id else None
    changed_at = changed_at or datetime.utcnow()

    lifecycle = ReviewLifecycle(
        owner_type=record.review_owner_kind,
        status=REVIEW_STATUS_SUBMITTED,
        submitted_at=changed_at,
        submitter_id=submitter_id,
    )
    transition = ReviewTransition(
        from_status=None,
        to_status=REVIEW_STATUS_SUBMITTED,
        changed_at=changed_at,
        actor_id=actor_id,
        actor_mode=actor_mode,
    )
    lifecycle.transitions.append(transition)
    record.review_owner_type = record.review_owner_kind
    record.review_lifecycle = lifecycle
    record.modified = changed_at
    return transition


def transition_reviewable(
    record,
    target_status,
    review_comment=None,
    actor_id=None,
    actor_mode=REVIEW_ACTOR_AUTHENTICATED,
    changed_at=None,
):
    """Append one valid transition and update current state without committing."""
    lifecycle = _current_lifecycle(record)
    if not hasattr(record, "modified"):
        raise ValueError("Reviewable record does not declare a modified timestamp.")
    if target_status not in ALLOWED_TRANSITIONS.get(lifecycle.status, set()):
        raise ValueError(
            f"Cannot transition reviewable record from {lifecycle.status!r} "
            f"to {target_status!r}."
        )

    actor_id = _actor(actor_id, actor_mode)
    comment = review_comment.strip() if review_comment else None
    if target_status in {REVIEW_STATUS_REVISION, REVIEW_STATUS_REJECTED} and not comment:
        raise ValueError("Revision and rejection require review feedback.")

    changed_at = changed_at or datetime.utcnow()
    transition = ReviewTransition(
        from_status=lifecycle.status,
        to_status=target_status,
        changed_at=changed_at,
        review_comment=comment,
        actor_id=actor_id,
        actor_mode=actor_mode,
    )
    lifecycle.transitions.append(transition)
    lifecycle.status = target_status
    record.modified = changed_at

    if target_status == REVIEW_STATUS_ACCEPTED:
        lifecycle.accepted_at = changed_at
        lifecycle.current_review_comment = None
    elif target_status in {REVIEW_STATUS_REVISION, REVIEW_STATUS_REJECTED}:
        lifecycle.current_review_comment = comment

    return transition
