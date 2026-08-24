from datetime import datetime
import unittest

from sqlalchemy.exc import IntegrityError

from application.database import db_session
from application.models import Dataset
from test.db import engine


class TestDatasetLifecycleConstraints(unittest.TestCase):
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
    def dataset(**overrides):
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
            "submitted_at": timestamp,
            "status": "submitted",
        }
        values.update(overrides)
        return Dataset(**values)

    def assert_constraint_rejects(self, constraint_name, **values):
        db_session.add(self.dataset(**values))
        with self.assertRaises(IntegrityError) as raised:
            db_session.commit()
        self.assertIn(constraint_name, str(raised.exception.orig))
        db_session.rollback()

    def test_status_must_be_a_supported_value(self):
        self.assert_constraint_rejects(
            "ck_Dataset_status",
            status="draft",
        )

    def test_accepted_status_requires_acceptance_timestamp(self):
        self.assert_constraint_rejects(
            "ck_Dataset_accepted_at",
            status="accepted",
            accepted_at=None,
        )

    def test_revision_requires_review_feedback(self):
        self.assert_constraint_rejects(
            "ck_Dataset_review_comment",
            status="revision",
            review_comment=None,
        )
