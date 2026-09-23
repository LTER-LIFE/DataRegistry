from datetime import datetime
import unittest
from unittest.mock import patch

from flask import Flask, session
from flask_admin import Admin

from application.admin import DatasetReviewAdmin
from application.authentication import has_editor_access, oidc_subject
from application.database import db_session
from application.models import (
    DataTheme,
    Dataset,
    Keyword,
    ReviewLifecycle,
    ReviewTransition,
)
from application.workflow import initialize_reviewable
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
        dataset = Dataset(
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
        )
        initialize_reviewable(dataset, changed_at=timestamp)
        return dataset

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

    @patch("application.authentication.get_userinfo")
    def test_oidc_subject_uses_authoritative_userinfo(self, get_userinfo):
        get_userinfo.return_value = {"sub": " reviewer-subject "}

        subject = oidc_subject({"access_token": "encoded-token"})

        self.assertEqual(subject, "reviewer-subject")
        get_userinfo.assert_called_once_with({"access_token": "encoded-token"})

    @patch("application.authentication.get_userinfo", return_value=None)
    def test_oidc_subject_is_none_without_authoritative_userinfo(self, get_userinfo):
        self.assertIsNone(oidc_subject({"access_token": "opaque-token"}))
        get_userinfo.assert_called_once()

    def test_enabled_bypass_lists_submitted_dataset_in_admin(self):
        app = self.app(local_bypass=True)
        admin = Admin(app, name="Test review")
        admin.add_view(DatasetReviewAdmin(Dataset, db_session))
        db_session.add(self.submitted_dataset())
        db_session.flush()

        response = app.test_client().get("/admin/dataset/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Locally reviewable submission", response.data)

    def test_admin_edit_updates_modified_timestamp(self):
        app = self.app(local_bypass=True)
        view = DatasetReviewAdmin(Dataset, db_session)
        dataset = self.submitted_dataset()
        db_session.add(dataset)
        db_session.commit()
        original_modified = dataset.modified

        with app.test_request_context(method="POST"):
            form = view.get_edit_form()(obj=dataset)
            self.assertNotIn("modified", form._fields)
            form.title.data = "Updated during local review"
            form.populate_obj(dataset)

        db_session.commit()

        self.assertEqual(dataset.title, "Updated during local review")
        self.assertGreater(dataset.modified, original_modified)

    def test_local_bypass_transition_records_honest_provenance(self):
        app = self.app(local_bypass=True)
        view = DatasetReviewAdmin(Dataset, db_session)
        dataset = self.submitted_dataset()
        db_session.add(dataset)
        db_session.commit()

        with app.test_request_context():
            result = view._transition_selected([dataset.dataset_id], "accepted")

        self.assertTrue(result)
        transitions = db_session.query(ReviewTransition).order_by(
            ReviewTransition.review_transition_id
        ).all()
        self.assertEqual(len(transitions), 2)
        self.assertIsNone(transitions[-1].actor_id)
        self.assertEqual(transitions[-1].actor_mode, "local_bypass")
        self.assertEqual(dataset.review_lifecycle.status, "accepted")

    @patch("application.admin.oidc_subject", return_value="reviewer-subject")
    def test_authenticated_transition_records_oidc_subject(self, subject):
        app = self.app(local_bypass=False)
        view = DatasetReviewAdmin(Dataset, db_session)
        dataset = self.submitted_dataset()
        db_session.add(dataset)
        db_session.commit()

        with app.test_request_context():
            session["access_token"] = {"access_token": "encoded-token"}
            result = view._transition_selected([dataset.dataset_id], "accepted")

        self.assertTrue(result)
        transition = db_session.query(ReviewTransition).order_by(
            ReviewTransition.review_transition_id.desc()
        ).first()
        self.assertEqual(transition.actor_id, "reviewer-subject")
        self.assertEqual(transition.actor_mode, "authenticated")
        subject.assert_called_once()

    def test_admin_deletion_removes_aggregate_but_not_shared_records(self):
        app = self.app(local_bypass=True)
        view = DatasetReviewAdmin(Dataset, db_session)
        dataset = self.submitted_dataset()
        keyword = Keyword(name="shared keyword")
        theme = DataTheme(code="shared-theme", label="Shared theme")
        dataset.dataset_keywords.append(keyword)
        dataset.dataset_themes.append(theme)
        db_session.add(dataset)
        db_session.commit()

        with app.test_request_context():
            result = view.delete_model(dataset)

        self.assertTrue(result)
        self.assertEqual(db_session.query(Dataset).count(), 0)
        self.assertEqual(db_session.query(ReviewLifecycle).count(), 0)
        self.assertEqual(db_session.query(ReviewTransition).count(), 0)
        self.assertEqual(db_session.query(Keyword).count(), 1)
        self.assertEqual(db_session.query(DataTheme).count(), 1)
