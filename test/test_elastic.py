import json
import unittest
from geoalchemy2 import load_spatialite
from sqlalchemy import create_engine
from sqlalchemy.event import listen
from sqlalchemy.testing import eq_

from application import db_session, validate_index
from application.models import metadata, Dataset, Location
from application.search_index import MAPPING

from config import Config
from mock_objects import MockObjects


class TestElasticDataset(unittest.TestCase):
    INDEX_NAME = "test_dataset"
    def setUp(self):
        """
        Setup function to build flask application in memory
        """
        engine = create_engine(echo=True, connect_args={"check_same_thread": False}, url='sqlite:///:memory:')

        if Config.SQLALCHEMY_DATABASE_URI.find("sqlite") > -1:
            listen(engine, "connect", load_spatialite)
        else:
            connect_args = {}

        db_session.configure(bind=engine)

        # To create tables, you typically do:
        metadata.create_all(engine)

        self.mock_objects = MockObjects()


        self.es = validate_index()

        """
        print("Run setup")
        self.es = Elasticsearch(['https://localhost:9200/'],
            basic_auth=("elastic", "wqv-7S75rA3tMKra7qvT"),
            verify_certs=True,
            ca_certs="/home/eric/Apps/elasticsearch-9.0.2/config/certs/http_ca.crt"

            )
        """

        self.mock_objects = MockObjects()

        print("Finished running setup")

    def tearDown(self):
        """
        Teardown database after use
        """
        db_session.remove()

    def test_elastic_search_connection(self):
        print(json.dumps(dict(self.es.info(human=True, pretty=True)), indent=1))
        assert self.es.ping()


    def test_create_index(self):
        self.recreate_index(self.INDEX_NAME)

    def test_create_single_dataset_and_index_it(self):
        self.recreate_index(self.INDEX_NAME)

        dataset = self.mock_objects.create_mock_dataset("-one")
        db_session.add(dataset)
        db_session.commit()
        db_session.flush()

        datasets = db_session.query(Dataset).all()

        print(datasets)
        assert len(datasets) == 1

        actions = []

        #for dataset in datasets:
        #    print(self.es.index(index=self.INDEX_NAME, body=dataset.to_dict()))

        print(f"indexed {len(datasets)} documents into Elasticsearch.")
        self.es.indices.refresh(index=self.INDEX_NAME)

        all_documents_query = {"query": {"match_all": {}}}
        results = self.es.search(index=self.INDEX_NAME, body=all_documents_query)
        print("Got %d Hits:" % results['hits']['total']['value'])
        print(results)



    def test_create_dataset(self):
        instances = db_session.query(Dataset).all()
        eq_(0, len(instances))

        dataset = self.mock_objects.generate_datasets(1, "dataset")

        db_session.add_all(dataset)
        db_session.commit()
        db_session.flush()

        all_db_datasets = db_session.query(Dataset).all()

        print(all_db_datasets[0].to_dict())

        assert len(all_db_datasets) == 1

    def recreate_index(self, index_name):
        if not self.es:
            self.es = validate_index()
        if not self.es.indices.exists(index=index_name):
            self.es.indices.create(index=index_name, mappings=MAPPING)
            print(f"Index '{index_name}' created with mapping.")
        else:
            self.es.indices.delete(index=index_name)
            self.es.indices.create(index=index_name, mappings=MAPPING)
            print(f"Index '{index_name}' recreated.")
if __name__ == '__main__':
    unittest.main()
