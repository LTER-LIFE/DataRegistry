from datetime import datetime, timedelta

from geoalchemy2 import load_spatialite
from sqlalchemy.event import listen
from sqlalchemy.testing import eq_

from application.database import db_session
from application.models import metadata, Dataset, Agent, Location, LicenseDocument
from sqlalchemy import create_engine
import unittest
from config import Config


class TestDataset(unittest.TestCase):

    def setUp(self):
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
        print("Finished running setup")

    def tearDown(self):
        db_session.remove()

    def test_create_dataset(self):
        instances = db_session.query(Dataset).all()
        eq_(0, len(instances))

        def to_dataset():
            dataset = Dataset()
            dataset.modified = datetime.now()
            dataset.release_date = datetime.now()
            dataset.language = "EN"
            dataset.title = "Title of the mock dataset"
            dataset.description = "Description of the mock dataset"
            dataset.resource_type = "Resource type of the mock dataset"
            dataset.temporal_coverage_start = datetime.now() - timedelta(days=1)
            dataset.temporal_coverage_end = datetime.now() + timedelta(days=1)
            dataset.temporal_resolution = "1"
            dataset.spatial_resolution = "1"
            dataset.taxonomic_coverage = "Rabbit"
            dataset.access_rights = "OPEN"

            eric = "e.kuijt@nioo.knaw.nl"
            stefan = "s.vriend@nioo.knaw.nl"
            # Fill creator -> Agent
            dataset.creator = Agent.add_or_update_agent(mbox=eric)
            # dataset_contact_point -> Agent
            dataset.dataset_contact_point = Agent.add_or_update_agent(mbox=eric)
            # publisher -> Agent
            dataset.publisher = Agent.add_or_update_agent(mbox=eric)

            # metadata_provider -> Agent
            dataset.dataset_metadata_provider = Agent.add_or_update_agent(mbox=stefan)
            # keywords -> Keyword

            # spatial_covarage -> Location
            # db_location = Location.add_or_update_location(geometry=self.spatial_covarage.data)
            dataset.dataset_spatial_covarage = Location.add_or_update_location(geometry="GEOMETRYCOLLECTION ("
                                                                                        "POLYGON ((5.661704 52.067003, "
                                                                                                  "5.848422 52.09401, "
                                                                                                  "5.917068 52.01294, "
                                                                                                  "5.680925 51.94527, "
                                                                                                  "5.661704 52.067003"
                                                                                                  "))"
                                                                                        ")")

            # licence -> LicenceDocument
            dataset.license = LicenseDocument(code="CC-BY-4.0")

            return dataset
        dataset = to_dataset()


        db_session.add(dataset)
        db_session.commit()
        db_session.flush()

        all_db_datasets = db_session.query(Dataset).all()

        print(all_db_datasets[0].serialize())

        assert len(all_db_datasets) == 1

    def test_create_dataset_box_wkt(self):
        instances = db_session.query(Dataset).all()
        eq_(0, len(instances))

        def to_dataset():
            dataset = Dataset()
            dataset.modified = datetime.now()
            dataset.release_date = datetime.now()
            dataset.language = "EN"
            dataset.title = "Title of the mock dataset"
            dataset.description = "Description of the mock dataset"
            dataset.resource_type = "Resource type of the mock dataset"
            dataset.temporal_coverage_start = datetime.now() - timedelta(days=1)
            dataset.temporal_coverage_end = datetime.now() + timedelta(days=1)
            dataset.temporal_resolution = "1"
            dataset.spatial_resolution = "1"
            dataset.taxonomic_coverage = "Rabbit"
            dataset.access_rights = "OPEN"

            eric = "e.kuijt@nioo.knaw.nl"
            stefan = "s.vriend@nioo.knaw.nl"
            # Fill creator -> Agent
            dataset.creator = Agent.add_or_update_agent(mbox=eric)
            # dataset_contact_point -> Agent
            dataset.dataset_contact_point = Agent.add_or_update_agent(mbox=eric)
            # publisher -> Agent
            dataset.publisher = Agent.add_or_update_agent(mbox=eric)

            # metadata_provider -> Agent
            dataset.metadata_provider = Agent.add_or_update_agent(mbox=stefan)
            # keywords -> Keyword

            # spatial_covarage -> Location
            # db_location = Location.add_or_update_location(geometry=self.spatial_covarage.data)
            dataset.dataset_spatial_covarage = Location.add_or_update_location(geometry="POLYGON((5.675194 52.089633, 5.675194 52.15877, 5.776763 52.15877, 5.776763 52.089633, 5.675194 52.089633))")

            # licence -> LicenceDocument
            dataset.license = LicenseDocument(code="CC-BY-4.0")

            return dataset
        dataset = to_dataset()
        db_session.add(dataset)
        db_session.commit()
        db_session.flush()

        all_db_datasets = db_session.query(Dataset).all()

        assert len(all_db_datasets) == 1


if __name__ == '__main__':
    unittest.main()
