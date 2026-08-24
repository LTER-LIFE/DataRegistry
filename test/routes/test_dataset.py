from flask import url_for

from application.database import db_session

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
            dataset = self.mock_objects.create_mock_dataset("submitted")
            dataset.status = "submitted"
            db_session.commit()

            response = self.client.get(
                url_for('main_bp.datasets_detail', dataset_id=dataset.dataset_id)
            )

            assert response.status_code == 404

    def test_export_removes_dataset_that_is_no_longer_accepted(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset("download")
            dataset.status = "revision"
            dataset.review_comment = "Changes requested"
            db_session.commit()
            with self.client.session_transaction() as client_session:
                client_session["download_list"] = [dataset.dataset_id]

            response = self.client.get(url_for('main_bp.export_download_list'))

            self.assertEqual(response.status_code, 302)
            with self.client.session_transaction() as client_session:
                self.assertEqual(client_session["download_list"], [])

    def test_dataset_detail_invalid_id(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset("invalid_id")

            base_url = url_for(
                'main_bp.datasets_detail',
                dataset_id=dataset.dataset_id,
            )

            response = self.client.get(base_url + 'ab')

            assert response.status_code == 404
