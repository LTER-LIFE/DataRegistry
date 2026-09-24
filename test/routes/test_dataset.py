from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from flask import url_for

from application.database import db_session
from application.models import (
    DataTheme,
    Dataset,
    Keyword,
    ReviewLifecycle,
    ReviewTransition,
)
from application.workflow import initialize_reviewable

from test.base_test_case import BaseTestCase
from test.db import engine
from test.capture_templates import captured_templates
from test.mock_objects import MockObjects


class TestDatasetRoutes(BaseTestCase):

    def setUp(self):
        # Setup database sessions and connections
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        db_session.configure(bind=self.connection, join_transaction_mode="create_savepoint")

        self.mock_objects = MockObjects(db_session=db_session)

    def tearDown(self):
        """
        Close database sessions and connections
        """
        with self.client.session_transaction() as client_session:
            client_session.clear()
        db_session.remove()

        # rollback - everything that happened with the session above
        # (including calls to commit()) is rolled back.
        self.transaction.rollback()

        self.connection.close()

    def test_datasets_overview(self):
        with captured_templates(self.app) as templates:
            with self.app.app_context():
                response = self.client.get(url_for('main_bp.datasets'))
                assert response.status_code == 200
                template, context = templates[0]
                assert template.name == 'dataset_table.html'

    def test_dataset_detail_200(self):
        with captured_templates(self.app) as templates:
            with self.app.app_context():
                dataset = self.mock_objects.create_mock_dataset("forestry")

                response = self.client.get(
                    url_for(
                        'main_bp.datasets_detail',
                        dataset_id=dataset.dataset_id
                    )
                )

                assert response.status_code == 200
                template, context = templates[0]
                assert template.name == 'dataset_detail.html'
                assert context['title'] == dataset.title
                self.assertEqual(context['dataset']['dataset_id'], dataset.dataset_id)

    def test_dataset_detail_non_existing_id(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset("not_found")
            # add arbitrary number to create non-existing id
            dataset_id = dataset.dataset_id + 10

            response = self.client.get(
                url_for('main_bp.datasets_detail', dataset_id=dataset_id)
            )

            assert response.status_code == 404

    def test_non_accepted_dataset_is_not_public(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset(
                "submitted",
                status="submitted",
            )

            response = self.client.get(
                url_for('main_bp.datasets_detail', dataset_id=dataset.dataset_id)
            )

            assert response.status_code == 404

    def test_local_admin_bypass_does_not_enable_direct_edit(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset("local-bypass")
            self.app.config["LOCAL_EDITOR_BYPASS"] = True
            try:
                response = self.client.get(f"/datasets/edit/{dataset.dataset_id}")
            finally:
                self.app.config["LOCAL_EDITOR_BYPASS"] = False

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, url_for("main_bp.login", _external=False))

    def test_export_removes_dataset_that_is_no_longer_accepted(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset(
                "download",
                status="revision",
                review_comment="Changes requested",
            )
            with self.client.session_transaction() as client_session:
                client_session["download_list"] = [dataset.dataset_id]

            response = self.client.get(url_for('main_bp.export_download_list'))

            self.assertEqual(response.status_code, 302)
            with self.client.session_transaction() as client_session:
                self.assertEqual(client_session["download_list"], [])

    def test_download_list_keeps_only_accepted_datasets(self):
        with self.app.app_context():
            accepted = self.mock_objects.create_mock_dataset("accepted-download")
            hidden = self.mock_objects.create_mock_dataset(
                "hidden-download",
                status="rejected",
            )
            with self.client.session_transaction() as client_session:
                client_session["download_list"] = [
                    accepted.dataset_id,
                    hidden.dataset_id,
                ]

            response = self.client.get(url_for("main_bp.download_list"))

            self.assertEqual(response.status_code, 200)
            with self.client.session_transaction() as client_session:
                self.assertEqual(
                    client_session["download_list"],
                    [accepted.dataset_id],
                )

    def test_non_accepted_dataset_cannot_be_added_to_download_list(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset(
                "hidden-add",
                status="submitted",
            )

            response = self.client.get(
                url_for(
                    "main_bp.add_to_download_list",
                    dataset_id=dataset.dataset_id,
                )
            )

            self.assertEqual(response.status_code, 404)

    @patch("application.routes.search_index.fetch_all")
    def test_search_results_are_revalidated_against_lifecycle(self, fetch_all):
        with self.app.app_context():
            accepted = self.mock_objects.create_mock_dataset("accepted-search")
            hidden = self.mock_objects.create_mock_dataset(
                "hidden-search",
                status="revision",
            )
            fetch_all.return_value = SimpleNamespace(
                raw={
                    "hits": {
                        "hits": [
                            {
                                "_source": {
                                    "dataset_id": accepted.dataset_id,
                                    "title": accepted.title,
                                }
                            },
                            {
                                "_source": {
                                    "dataset_id": hidden.dataset_id,
                                    "title": hidden.title,
                                }
                            },
                        ],
                        "total": {"value": 2, "relation": "eq"},
                    }
                }
            )

            response = self.client.post("/query", json={})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"]["value"], 1)
        self.assertEqual(
            payload["hits"][0]["_source"]["dataset_id"],
            accepted.dataset_id,
        )

    @patch("application.routes.search_index.rebuild_index")
    def test_rebuild_selects_only_accepted_lifecycles(self, rebuild_index):
        rebuild_index.return_value = []
        with self.app.app_context():
            accepted = self.mock_objects.create_mock_dataset("accepted-rebuild")
            self.mock_objects.create_mock_dataset(
                "hidden-rebuild",
                status="submitted",
            )

            response = self.client.get("/rebuild")

        self.assertEqual(response.status_code, 200)
        rebuilt = rebuild_index.call_args.args[0]
        self.assertEqual([dataset.dataset_id for dataset in rebuilt], [accepted.dataset_id])

    def test_dataset_detail_invalid_id(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset("invalid_id")

            base_url = url_for(
                'main_bp.datasets_detail',
                dataset_id=dataset.dataset_id,
            )

            response = self.client.get(base_url + 'ab')

            assert response.status_code == 404

    @patch("application.routes.in_editor_group", return_value=True)
    @patch("application.routes.is_logged_in", return_value=True)
    def test_direct_delete_removes_lifecycle_but_retains_shared_records(
        self,
        is_logged_in,
        in_editor_group,
    ):
        timestamp = datetime(2026, 1, 1, 12, 0)
        dataset = Dataset(
            release_date=timestamp,
            language="EN",
            title="Dataset to delete",
            description="Delete through the lifecycle aggregate.",
            resource_type="dataset",
            temporal_coverage_start=datetime(2020, 1, 1),
            temporal_resolution="P1D",
            access_rights="open access",
            modified=timestamp,
        )
        initialize_reviewable(dataset, changed_at=timestamp)
        dataset.dataset_keywords.append(Keyword(name="shared keyword"))
        dataset.dataset_themes.append(
            DataTheme(code="shared-theme", label="Shared theme")
        )
        db_session.add(dataset)
        db_session.commit()

        response = self.client.get(f"/datasets/delete/{dataset.dataset_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(db_session.query(Dataset).count(), 0)
        self.assertEqual(db_session.query(ReviewLifecycle).count(), 0)
        self.assertEqual(db_session.query(ReviewTransition).count(), 0)
        self.assertEqual(db_session.query(Keyword).count(), 1)
        self.assertEqual(db_session.query(DataTheme).count(), 1)
        is_logged_in.assert_called_once()
        in_editor_group.assert_called_once()
