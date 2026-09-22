from datetime import datetime
import unittest

from sqlalchemy.exc import IntegrityError

from application.database import db_session
from application.models import Dataset, ReviewLifecycle, ReviewTransition
from test.db import engine


class TestReviewLifecycleConstraints(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        db_session.configure(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )

    def tearDown(self):
        db_session.rollback()
        db_session.remove()
        self.transaction.rollback()
        self.connection.close()

    @staticmethod
    def lifecycle(**overrides):
        values = {
            "owner_type": "dataset",
            "status": "submitted",
            "submitted_at": datetime(2026, 1, 1, 12, 0),
        }
        values.update(overrides)
        return ReviewLifecycle(**values)

    @staticmethod
    def dataset(review_lifecycle, **overrides):
        timestamp = datetime(2026, 1, 1, 12, 0)
        values = {
            "release_date": timestamp,
            "language": "EN",
            "title": "Constraint fixture",
            "description": "Metadata used to verify lifecycle constraints.",
            "resource_type": "dataset",
            "temporal_coverage_start": datetime(2020, 1, 1),
            "temporal_coverage_end": datetime(2021, 1, 1),
            "temporal_resolution": "P1D",
            "access_rights": "open access",
            "modified": timestamp,
        }
        if review_lifecycle is not None:
            values["review_lifecycle"] = review_lifecycle
        values.update(overrides)
        return Dataset(**values)

    @staticmethod
    def transition(review_lifecycle, **overrides):
        values = {
            "review_lifecycle": review_lifecycle,
            "from_status": None,
            "to_status": "submitted",
            "changed_at": datetime(2026, 1, 1, 12, 0),
            "actor_mode": "anonymous",
        }
        values.update(overrides)
        return ReviewTransition(**values)

    def assert_constraint_rejects(self, constraint_name, instance):
        db_session.add(instance)
        with self.assertRaises(IntegrityError) as raised:
            db_session.commit()
        self.assertIn(constraint_name, str(raised.exception.orig))
        db_session.rollback()

    def test_status_must_be_a_supported_value(self):
        self.assert_constraint_rejects(
            "ck_ReviewLifecycle_status",
            self.lifecycle(status="draft"),
        )

    def test_accepted_status_requires_acceptance_timestamp(self):
        self.assert_constraint_rejects(
            "ck_ReviewLifecycle_accepted_at",
            self.lifecycle(status="accepted", accepted_at=None),
        )

    def test_revision_and_rejection_require_review_feedback(self):
        for status, comment in (("revision", None), ("rejected", "  ")):
            with self.subTest(status=status):
                self.assert_constraint_rejects(
                    "ck_ReviewLifecycle_review_comment",
                    self.lifecycle(
                        status=status,
                        current_review_comment=comment,
                    ),
                )

    def test_lifecycle_owner_type_must_be_supported(self):
        self.assert_constraint_rejects(
            "ck_ReviewLifecycle_owner_type",
            self.lifecycle(owner_type="research_site"),
        )

    def test_dataset_owner_type_is_fixed(self):
        lifecycle = self.lifecycle()
        db_session.add(lifecycle)
        db_session.flush()
        dataset = self.dataset(
            None,
            review_lifecycle_id=lifecycle.review_lifecycle_id,
            review_owner_type="research_site",
        )
        self.assert_constraint_rejects(
            "ck_Dataset_review_owner_type",
            dataset,
        )

    def test_dataset_relationship_populates_typed_owner_reference(self):
        lifecycle = self.lifecycle()
        dataset = self.dataset(lifecycle)
        db_session.add(dataset)

        db_session.commit()

        self.assertEqual(dataset.review_lifecycle_id, lifecycle.review_lifecycle_id)
        self.assertEqual(dataset.review_owner_type, "dataset")
        self.assertIs(lifecycle.dataset, dataset)

    def test_one_lifecycle_cannot_be_assigned_to_two_datasets(self):
        lifecycle = self.lifecycle()
        db_session.add(lifecycle)
        db_session.flush()
        db_session.add_all(
            [
                self.dataset(
                    None,
                    review_lifecycle_id=lifecycle.review_lifecycle_id,
                    review_owner_type="dataset",
                    title="First owner",
                ),
                self.dataset(
                    None,
                    review_lifecycle_id=lifecycle.review_lifecycle_id,
                    review_owner_type="dataset",
                    title="Second owner",
                ),
            ]
        )

        with self.assertRaises(IntegrityError) as raised:
            db_session.commit()

        self.assertIn(
            "uq_Dataset_review_lifecycle_id",
            str(raised.exception.orig),
        )

    def test_transition_target_status_must_be_supported(self):
        lifecycle = self.lifecycle()
        self.assert_constraint_rejects(
            "ck_ReviewTransition_to_status",
            self.transition(lifecycle, to_status="draft"),
        )

    def test_revision_transition_requires_feedback(self):
        lifecycle = self.lifecycle()
        self.assert_constraint_rejects(
            "ck_ReviewTransition_review_comment",
            self.transition(
                lifecycle,
                from_status="submitted",
                to_status="revision",
            ),
        )

    def test_authenticated_transition_requires_actor_identity(self):
        lifecycle = self.lifecycle()
        self.assert_constraint_rejects(
            "ck_ReviewTransition_actor_identity",
            self.transition(
                lifecycle,
                actor_mode="authenticated",
                actor_id=None,
            ),
        )

    def test_non_authenticated_transition_rejects_actor_identity(self):
        lifecycle = self.lifecycle()
        self.assert_constraint_rejects(
            "ck_ReviewTransition_actor_identity",
            self.transition(
                lifecycle,
                actor_mode="migration",
                actor_id="invented-identity",
            ),
        )

    def test_transition_must_change_state(self):
        lifecycle = self.lifecycle()
        self.assert_constraint_rejects(
            "ck_ReviewTransition_state_change",
            self.transition(
                lifecycle,
                from_status="submitted",
                to_status="submitted",
            ),
        )
