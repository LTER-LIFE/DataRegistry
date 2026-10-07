from datetime import datetime
import unittest

from sqlalchemy.orm import sessionmaker

from application.models import Dataset, ReviewTransition
from application.workflow import initialize_reviewable, transition_reviewable
from test.db import engine
from test.mock_objects import MockObjects


# Direct minimal construction is intentional here: lifecycle initialization and
# invalid intermediate states are the behavior under test.
class TestReviewWorkflow(unittest.TestCase):
    @staticmethod
    def dataset(status="submitted"):
        dataset = Dataset(modified=datetime(2026, 1, 1))
        initialize_reviewable(
            dataset,
            changed_at=datetime(2026, 1, 1),
        )
        dataset.review_lifecycle.status = status
        return dataset

    def test_initialization_creates_submitted_lifecycle_and_event(self):
        dataset = Dataset(modified=datetime(2025, 1, 1))
        changed_at = datetime(2026, 1, 1, 12, 30)

        transition = initialize_reviewable(
            dataset,
            submitter_id="submitter-subject",
            actor_id="submitter-subject",
            actor_mode="authenticated",
            changed_at=changed_at,
        )

        lifecycle = dataset.review_lifecycle
        self.assertEqual(dataset.review_owner_type, "dataset")
        self.assertEqual(dataset.modified, changed_at)
        self.assertEqual(lifecycle.status, "submitted")
        self.assertEqual(lifecycle.submitted_at, changed_at)
        self.assertEqual(lifecycle.submitter_id, "submitter-subject")
        self.assertIsNone(transition.from_status)
        self.assertEqual(transition.to_status, "submitted")
        self.assertEqual(transition.actor_id, "submitter-subject")
        self.assertEqual(transition.actor_mode, "authenticated")
        self.assertEqual(lifecycle.transitions, [transition])

    def test_record_cannot_be_initialized_twice(self):
        dataset = self.dataset()

        with self.assertRaisesRegex(ValueError, "already has a lifecycle"):
            initialize_reviewable(dataset)

        self.assertEqual(len(dataset.review_lifecycle.transitions), 1)

    def test_accept_sets_acceptance_time_and_clears_comment(self):
        dataset = self.dataset()
        dataset.review_lifecycle.current_review_comment = "old feedback"
        changed_at = datetime(2026, 2, 1, 12, 30)

        transition = transition_reviewable(
            dataset,
            "accepted",
            actor_id="reviewer-subject",
            changed_at=changed_at,
        )

        lifecycle = dataset.review_lifecycle
        self.assertEqual(lifecycle.status, "accepted")
        self.assertEqual(lifecycle.accepted_at, changed_at)
        self.assertEqual(dataset.modified, changed_at)
        self.assertIsNone(lifecycle.current_review_comment)
        self.assertEqual(transition.from_status, "submitted")
        self.assertEqual(transition.to_status, "accepted")
        self.assertEqual(transition.actor_id, "reviewer-subject")
        self.assertEqual(len(lifecycle.transitions), 2)

    def test_revision_requires_feedback_without_mutating_state(self):
        dataset = self.dataset()
        lifecycle = dataset.review_lifecycle
        original_modified = dataset.modified

        with self.assertRaisesRegex(ValueError, "require review feedback"):
            transition_reviewable(
                dataset,
                "revision",
                actor_id="reviewer-subject",
            )

        self.assertEqual(lifecycle.status, "submitted")
        self.assertEqual(dataset.modified, original_modified)
        self.assertEqual(len(lifecycle.transitions), 1)

    def test_accepted_record_can_return_to_revision(self):
        dataset = self.dataset("accepted")
        dataset.review_lifecycle.accepted_at = datetime(2026, 1, 2)

        transition_reviewable(
            dataset,
            "revision",
            "Please clarify the location.",
            actor_id="reviewer-subject",
        )

        lifecycle = dataset.review_lifecycle
        self.assertEqual(lifecycle.status, "revision")
        self.assertEqual(
            lifecycle.current_review_comment,
            "Please clarify the location.",
        )
        self.assertEqual(lifecycle.accepted_at, datetime(2026, 1, 2))

    def test_rejected_record_can_be_reopened(self):
        dataset = self.dataset("rejected")
        dataset.review_lifecycle.current_review_comment = "Original rejection"

        transition_reviewable(
            dataset,
            "revision",
            "Reopened after follow-up.",
            actor_id="reviewer-subject",
        )

        self.assertEqual(dataset.review_lifecycle.status, "revision")

    def test_resubmission_preserves_current_revision_feedback(self):
        dataset = self.dataset("revision")
        dataset.review_lifecycle.current_review_comment = "Clarify the methods."

        transition_reviewable(
            dataset,
            "submitted",
            actor_id="submitter-subject",
        )

        self.assertEqual(dataset.review_lifecycle.status, "submitted")
        self.assertEqual(
            dataset.review_lifecycle.current_review_comment,
            "Clarify the methods.",
        )

    def test_revision_must_be_resubmitted_before_acceptance(self):
        dataset = self.dataset("revision")
        lifecycle = dataset.review_lifecycle

        with self.assertRaisesRegex(ValueError, "Cannot transition"):
            transition_reviewable(
                dataset,
                "accepted",
                actor_id="reviewer-subject",
            )

        self.assertEqual(lifecycle.status, "revision")
        self.assertEqual(len(lifecycle.transitions), 1)

    def test_local_bypass_transition_has_no_fabricated_identity(self):
        dataset = self.dataset()

        transition = transition_reviewable(
            dataset,
            "accepted",
            actor_mode="local_bypass",
        )

        self.assertIsNone(transition.actor_id)
        self.assertEqual(transition.actor_mode, "local_bypass")

    def test_authenticated_activity_requires_identity(self):
        dataset = self.dataset()

        with self.assertRaisesRegex(ValueError, "requires an actor identity"):
            transition_reviewable(dataset, "accepted")

        self.assertEqual(dataset.review_lifecycle.status, "submitted")
        self.assertEqual(len(dataset.review_lifecycle.transitions), 1)


class TestPersistedReviewWorkflow(unittest.TestCase):
    def test_stale_reviewer_state_is_refreshed_under_row_lock(self):
        timestamp = datetime(2026, 1, 1, 12, 0)
        session_factory = sessionmaker(bind=engine)
        setup_session = session_factory()
        dataset = MockObjects(db_session=setup_session).create_mock_dataset(
            "concurrent-review",
            status="submitted",
            persist=False,
            changed_at=timestamp,
            include_related=False,
            dataset_overrides={
                "title": "Concurrent review fixture",
                "description": "Verify serialized lifecycle transitions.",
            },
        )
        setup_session.add(dataset)
        setup_session.commit()
        dataset_id = dataset.dataset_id
        setup_session.close()

        first_session = session_factory()
        second_session = session_factory()
        first_record = first_session.get(Dataset, dataset_id)
        second_record = second_session.get(Dataset, dataset_id)
        self.assertEqual(second_record.review_lifecycle.status, "submitted")

        try:
            transition_reviewable(
                first_record,
                "accepted",
                actor_id="first-reviewer",
            )
            first_session.commit()

            with self.assertRaisesRegex(ValueError, "Cannot transition"):
                transition_reviewable(
                    second_record,
                    "rejected",
                    "Conflicting decision",
                    actor_id="second-reviewer",
                )
            second_session.rollback()
        finally:
            first_session.close()
            second_session.close()

        verification_session = session_factory()
        try:
            persisted = verification_session.get(Dataset, dataset_id)
            self.assertEqual(persisted.review_lifecycle.status, "accepted")
            self.assertEqual(
                verification_session.query(ReviewTransition).filter_by(
                    review_lifecycle_id=persisted.review_lifecycle_id
                ).count(),
                2,
            )
            verification_session.delete(persisted.review_lifecycle)
            verification_session.commit()
        finally:
            verification_session.close()
