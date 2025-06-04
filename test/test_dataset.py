import json
from datetime import datetime, timedelta
from geoalchemy2 import load_spatialite
from sqlalchemy.event import listen
from sqlalchemy.testing import eq_

from application.database import db_session
from application.models import metadata, Dataset, Agent, Location, LicenseDocument
from sqlalchemy import create_engine
import unittest

from config import Config
from mock_objects import MockObjects


class TestDataset(unittest.TestCase):

    def setUp(self):
        """
        Setup function to build flask application in memory
        """
        print("Run setup")
        engine = create_engine(echo=True, connect_args={"check_same_thread": False}, url='sqlite:///:memory:')

        if Config.SQLALCHEMY_DATABASE_URI.find("sqlite") > -1:
            listen(engine, "connect", load_spatialite)
        else:
            connect_args = {}

        db_session.configure(bind=engine)
        # You probably need to create some tables and
        # load some test data, do so here.

        # To create tables, you typically do:
        metadata.create_all(engine)

        self.mock_objects = MockObjects()

        print("Finished running setup")

    def tearDown(self):
        """
        Teardown database after use
        """
        db_session.remove()

    def test_create_dataset(self):
        instances = db_session.query(Dataset).all()
        eq_(0, len(instances))

        dataset = self.mock_objects.create_mock_dataset("one")

        db_session.add(dataset)
        db_session.commit()
        db_session.flush()

        all_db_datasets = db_session.query(Dataset).all()

        print(json.dumps(all_db_datasets[0].to_dict(), indent=1))

        assert len(all_db_datasets) == 1

    def test_create_dataset_box_wkt(self):
        instances = db_session.query(Dataset).all()
        eq_(0, len(instances))

        dataset = self.mock_objects.create_mock_dataset("two")
        db_session.add(dataset)
        db_session.commit()
        db_session.flush()

        all_db_datasets = db_session.query(Dataset).all()

        assert len(all_db_datasets) == 1

    def test_create_dataset_from_shapefile(self):
        shapefile_path = "shapefile/veluwe.zip"

        Location.from_shapefile(shapefile_path, persist=True)

        db_session.commit()
        db_session.flush()

        all_db_locations = db_session.query(Location).all()

        assert len(all_db_locations) == 1

        print(all_db_locations[0].to_shape(field="bbox", to="wkt"))
        print(all_db_locations[0].to_shape(field="centroid", to="wkt"))


if __name__ == '__main__':
    unittest.main()
