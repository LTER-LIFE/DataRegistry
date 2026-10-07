from types import SimpleNamespace
from unittest.mock import patch

from application.database import db_session
from test.base_test_case import BaseTestCase
from test.capture_templates import captured_templates
from test.db import engine
from test.mock_objects import MockObjects


class TestDashboardRoutes(BaseTestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        db_session.configure(bind=self.connection, join_transaction_mode="create_savepoint")
        self.mock_objects = MockObjects(db_session=db_session)

    def tearDown(self):
        db_session.remove()
        self.transaction.rollback()
        self.connection.close()

    @patch("application.routes.search_index.fetch_all")
    def test_dashboard_reports_lifecycle_and_actual_index_counts(self, fetch_all):
        fetch_all.return_value = SimpleNamespace(
            body={"hits": {"total": {"value": 7, "relation": "eq"}}},
            meta=SimpleNamespace(duration=0.01),
        )
        db_session.add_all(
            [
                self.mock_objects.create_mock_dataset(
                    f"dashboard-{status}",
                    status=status,
                    persist=False,
                    include_related=False,
                )
                for status in ("accepted", "submitted", "revision", "rejected")
            ]
        )
        db_session.flush()

        with captured_templates(self.app) as templates:
            response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        template, context = templates[0]
        self.assertEqual(template.name, "dashboard.html")
        self.assertEqual(context["database_datasets_stats"]["total"], 4)
        self.assertEqual(context["database_datasets_stats"]["submitted"], 1)
        self.assertEqual(context["database_datasets_stats"]["revision"], 1)
        self.assertEqual(context["database_datasets_stats"]["rejected"], 1)
        self.assertEqual(context["database_datasets_stats"]["accepted"], 1)
        self.assertEqual(context["index_datasets_stats"]["total"], 7)
        self.assertIn(b"Accepted in Elasticsearch: 7", response.data)
        self.assertIn(b"do not match accepted datasets", response.data)
