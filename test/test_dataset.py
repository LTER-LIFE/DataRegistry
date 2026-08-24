import os
from sqlalchemy.testing import eq_

from application.database import db_session
from application.models import Dataset, Location
import unittest

from test.base_test_case import BaseTestCase
from test.db import engine
from test.mock_objects import MockObjects


class TestDataset(BaseTestCase):

    def setUp(self):
        """
        Setup database sessions and connections
        """
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

    def test_create_dataset(self):
        instances = db_session.query(Dataset).all()
        eq_(0, len(instances))

        with self.app.app_context():
            self.mock_objects.create_mock_dataset("one")

        all_db_datasets = db_session.query(Dataset).all()

        assert len(all_db_datasets) == 1
        assert all_db_datasets[0].status == "accepted"
        assert all_db_datasets[0].submitted_at is not None
        assert all_db_datasets[0].accepted_at is not None

    def test_create_dataset_box_wkt(self):
        instances = db_session.query(Dataset).all()
        eq_(0, len(instances))

        with self.app.app_context():
            self.mock_objects.create_mock_dataset("two")

        all_db_datasets = db_session.query(Dataset).all()

        assert len(all_db_datasets) == 1

    def test_catalog_serialization_excludes_non_accepted_siblings(self):
        with self.app.app_context():
            accepted = self.mock_objects.create_mock_dataset("accepted")
            hidden = self.mock_objects.create_mock_dataset("hidden")
            hidden.dataset_catalog = accepted.dataset_catalog
            hidden.status = "revision"
            hidden.review_comment = "Changes requested"
            db_session.commit()

            serialized = accepted.to_dict()

            catalogued_ids = {
                dataset["dataset_id"]
                for dataset in serialized["dataset_catalog"]["datasets_in_catalogue"]
            }
            self.assertIn(accepted.dataset_id, catalogued_ids)
            self.assertNotIn(hidden.dataset_id, catalogued_ids)

    def test_create_dataset_from_shapefile(self):
        dirname = os.path.dirname(__file__)
        shapefile_path = os.path.join(dirname, "shapefile/veluwe.zip")

        Location.from_shapefile(shapefile_path, persist=True)

        db_session.commit()
        db_session.flush()

        all_db_locations = db_session.query(Location).all()

        assert len(all_db_locations) == 1

        print(all_db_locations[0].to_shape(field="bbox", to="wkt"))
        print(all_db_locations[0].to_shape(field="centroid", to="wkt"))


if __name__ == '__main__':
    unittest.main()
