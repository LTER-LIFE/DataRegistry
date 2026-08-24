from datetime import datetime
import uuid

from application import search_index
from application.database import db_session
from application.models import Dataset
from application.workflow import transition_dataset
from test.base_test_case import BaseTestCase
from test.db import engine


class TestLiveSearchSynchronization(BaseTestCase):
    def setUp(self):
        db_session.remove()
        db_session.configure(bind=engine)
        self.index_name = f"dataset-test-{uuid.uuid4().hex}"
        self.original_index_name = search_index.INDEX_NAME
        search_index.INDEX_NAME = self.index_name
        search_index.es.indices.create(
            index=self.index_name,
            mappings=search_index.MAPPING,
        )

    def tearDown(self):
        db_session.rollback()
        db_session.remove()
        search_index.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        search_index.INDEX_NAME = self.original_index_name

    @staticmethod
    def dataset():
        timestamp = datetime(2026, 1, 1, 12, 0)
        return Dataset(
            release_date=timestamp,
            language="EN",
            title="Search synchronization fixture",
            description="Metadata used to verify live search synchronization.",
            resource_type="dataset",
            temporal_coverage_start=datetime(2020, 1, 1),
            temporal_coverage_end=datetime(2021, 1, 1),
            temporal_resolution="P1D",
            access_rights="open access",
            modified=timestamp,
            submitted_at=timestamp,
            status="submitted",
        )

    def refresh_index(self):
        search_index.es.indices.refresh(index=self.index_name)

    def test_committed_status_transitions_update_the_live_index(self):
        with self.app.app_context():
            dataset = self.dataset()
            db_session.add(dataset)
            db_session.commit()
            dataset_id = dataset.dataset_id
            self.refresh_index()
            self.assertFalse(
                search_index.es.exists(index=self.index_name, id=dataset_id)
            )

            transition_dataset(dataset, "accepted")
            db_session.commit()
            self.refresh_index()
            indexed = search_index.es.get(index=self.index_name, id=dataset_id)
            self.assertEqual(indexed["_source"]["status"], "accepted")
            self.assertEqual(
                indexed["_source"]["title"], "Search synchronization fixture"
            )

            dataset.title = "Updated accepted metadata"
            db_session.commit()
            self.refresh_index()
            indexed = search_index.es.get(index=self.index_name, id=dataset_id)
            self.assertEqual(indexed["_source"]["title"], "Updated accepted metadata")

            transition_dataset(dataset, "revision", "Please revise the description.")
            db_session.commit()
            self.refresh_index()
            self.assertFalse(
                search_index.es.exists(index=self.index_name, id=dataset_id)
            )

            db_session.delete(dataset)
            db_session.commit()
