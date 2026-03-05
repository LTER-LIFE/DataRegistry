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

    def test_dataset_detail_invalid_id(self):
        with self.app.app_context():
            dataset = self.mock_objects.create_mock_dataset("invalid_id")

            base_url = url_for(
                'main_bp.datasets_detail',
                dataset_id=dataset.dataset_id,
            )

            response = self.client.get(base_url + 'ab')

            assert response.status_code == 404
