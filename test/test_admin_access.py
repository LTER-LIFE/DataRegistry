from datetime import datetime
import unittest
from unittest.mock import patch

from flask import Flask
from flask_admin import Admin

from application.admin import DatasetReviewAdmin
from application.authentication import has_editor_access
from application.database import db_session
from application.models import Dataset
from test.db import engine


class TestLocalEditorBypass(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        db_session.configure(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )

    def tearDown(self):
        db_session.remove()
        self.transaction.rollback()
        self.connection.close()

    @staticmethod
    def app(local_bypass):
        app = Flask(__name__)
        app.config.update(
            SECRET_KEY="test-secret",
            LOCAL_EDITOR_BYPASS=local_bypass,
            WTF_CSRF_ENABLED=False,
        )
        return app

    @staticmethod
    def submitted_dataset():
        timestamp = datetime(2026, 1, 1, 12, 0)
        return Dataset(
            release_date=timestamp,
            language="EN",
            title="Locally reviewable submission",
            description="Submitted metadata for local admin inspection.",
            resource_type="dataset",
            temporal_coverage_start=datetime(2020, 1, 1),
            temporal_coverage_end=datetime(2021, 1, 1),
            temporal_resolution="P1D",
            access_rights="open access",
            modified=timestamp,
            submitted_at=timestamp,
            status="submitted",
        )

    @patch("application.authentication.in_editor_group")
    def test_disabled_bypass_uses_sram_editor_policy(self, in_editor_group):
        in_editor_group.return_value = False
        app = self.app(local_bypass=False)

        with app.test_request_context():
            self.assertFalse(has_editor_access(None))

        in_editor_group.assert_called_once_with(None)

    @patch("application.authentication.in_editor_group")
    def test_enabled_bypass_does_not_contact_sram(self, in_editor_group):
        app = self.app(local_bypass=True)

        with app.test_request_context():
            self.assertTrue(has_editor_access(None))

        in_editor_group.assert_not_called()

    def test_enabled_bypass_lists_submitted_dataset_in_admin(self):
        app = self.app(local_bypass=True)
        admin = Admin(app, name="Test review")
        admin.add_view(DatasetReviewAdmin(Dataset, db_session))
        db_session.add(self.submitted_dataset())
        db_session.flush()

        response = app.test_client().get("/admin/dataset/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Locally reviewable submission", response.data)
