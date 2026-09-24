from datetime import datetime
import uuid
from unittest.mock import patch

from application import search_index
from application.database import db_session
from application.models import (
    Dataset,
    ReviewLifecycle,
    REVIEW_ACTOR_SYSTEM,
)
from application.workflow import initialize_reviewable, transition_reviewable
from test.base_test_case import BaseTestCase
from test.db import engine


class TestLiveSearchSynchronization(BaseTestCase):
    def setUp(self):
        db_session.remove()
        db_session.configure(bind=engine)
        self.lifecycle_ids = set()
        self.index_name = f"dataset-test-{uuid.uuid4().hex}"
        self.original_index_name = search_index.INDEX_NAME
        search_index.INDEX_NAME = self.index_name
        search_index.es.indices.create(
            index=self.index_name,
            mappings=search_index.MAPPING,
        )

    def tearDown(self):
        db_session.rollback()
        for lifecycle_id in self.lifecycle_ids:
            lifecycle = db_session.get(ReviewLifecycle, lifecycle_id)
            if lifecycle is not None:
                db_session.delete(lifecycle)
        db_session.commit()
        db_session.remove()
        search_index.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        search_index.INDEX_NAME = self.original_index_name

    @staticmethod
    def dataset(title="Search synchronization fixture"):
        timestamp = datetime(2026, 1, 1, 12, 0)
        dataset = Dataset(
            release_date=timestamp,
            language="EN",
            title=title,
            description="Metadata used to verify live search synchronization.",
            resource_type="dataset",
            temporal_coverage_start=datetime(2020, 1, 1),
            temporal_coverage_end=datetime(2021, 1, 1),
            temporal_resolution="P1D",
            access_rights="open access",
            modified=timestamp,
        )
        initialize_reviewable(
            dataset,
            actor_mode=REVIEW_ACTOR_SYSTEM,
            changed_at=timestamp,
        )
        return dataset

    def commit_dataset(self, title="Search synchronization fixture"):
        dataset = self.dataset(title)
        db_session.add(dataset)
        db_session.commit()
        self.lifecycle_ids.add(dataset.review_lifecycle_id)
        return dataset

    @staticmethod
    def accept(dataset):
        transition_reviewable(
            dataset,
            "accepted",
            actor_mode=REVIEW_ACTOR_SYSTEM,
            changed_at=datetime(2026, 1, 2, 12, 0),
        )

    def refresh_index(self):
        search_index.es.indices.refresh(index=self.index_name)

    def test_committed_lifecycle_and_metadata_changes_update_live_index(self):
        with self.app.app_context():
            dataset = self.commit_dataset()
            dataset_id = dataset.dataset_id
            self.refresh_index()
            self.assertFalse(
                search_index.es.exists(index=self.index_name, id=dataset_id)
            )

            self.accept(dataset)
            db_session.commit()
            self.refresh_index()
            indexed = search_index.es.get(index=self.index_name, id=dataset_id)
            self.assertEqual(indexed["_source"]["status"], "accepted")
            self.assertEqual(
                indexed["_source"]["title"], "Search synchronization fixture"
            )

            accepted_modified = dataset.modified
            dataset.title = "Updated accepted metadata"
            db_session.commit()
            self.assertGreater(dataset.modified, accepted_modified)
            self.refresh_index()
            indexed = search_index.es.get(index=self.index_name, id=dataset_id)
            self.assertEqual(indexed["_source"]["title"], "Updated accepted metadata")

            transition_reviewable(
                dataset,
                "revision",
                "Please revise the description.",
                actor_mode=REVIEW_ACTOR_SYSTEM,
            )
            db_session.commit()
            self.refresh_index()
            self.assertFalse(
                search_index.es.exists(index=self.index_name, id=dataset_id)
            )

    def test_lifecycle_only_change_updates_owner_and_index(self):
        with self.app.app_context():
            dataset = self.commit_dataset("Lifecycle-only synchronization")
            self.accept(dataset)
            db_session.commit()
            original_modified = dataset.modified

            dataset.review_lifecycle.submitter_id = "updated-submitter"
            db_session.commit()

            self.assertGreater(dataset.modified, original_modified)
            self.refresh_index()
            indexed = search_index.es.get(
                index=self.index_name,
                id=dataset.dataset_id,
            )
            self.assertEqual(
                indexed["_source"]["modified"],
                dataset.to_dict()["modified"],
            )
            self.assertNotIn("submitter_id", indexed["_source"])

    def test_deleting_accepted_lifecycle_removes_document(self):
        with self.app.app_context():
            dataset = self.commit_dataset("Deleted lifecycle")
            self.accept(dataset)
            db_session.commit()
            dataset_id = dataset.dataset_id
            self.refresh_index()
            self.assertTrue(
                search_index.es.exists(index=self.index_name, id=dataset_id)
            )

            db_session.delete(dataset.review_lifecycle)
            db_session.commit()

            self.refresh_index()
            self.assertIsNone(db_session.get(Dataset, dataset_id))
            self.assertFalse(
                search_index.es.exists(index=self.index_name, id=dataset_id)
            )

    def test_rollback_discards_pending_synchronization(self):
        with self.app.app_context():
            dataset = self.commit_dataset("Committed title")
            self.accept(dataset)
            db_session.commit()
            dataset_id = dataset.dataset_id
            self.refresh_index()

            dataset.title = "Rolled back title"
            db_session.flush()

            self.assertIn(
                ("dataset", dataset_id),
                db_session.info["reviewable_sync_keys"],
            )
            self.refresh_index()
            indexed = search_index.es.get(index=self.index_name, id=dataset_id)
            self.assertEqual(indexed["_source"]["title"], "Committed title")

            db_session.rollback()

            self.assertNotIn("reviewable_sync_keys", db_session.info)
            self.refresh_index()
            indexed = search_index.es.get(index=self.index_name, id=dataset_id)
            self.assertEqual(indexed["_source"]["title"], "Committed title")

    def test_queue_deduplicates_and_continues_after_sync_failure(self):
        with self.app.app_context():
            first = self.dataset("First queued dataset")
            second = self.dataset("Second queued dataset")
            db_session.add_all((first, second))
            db_session.commit()
            self.lifecycle_ids.update(
                (first.review_lifecycle_id, second.review_lifecycle_id)
            )

            self.accept(first)
            self.accept(second)
            first.title = "First updated title"
            first.description = "First updated description"
            first.review_lifecycle.submitter_id = "updated-submitter"

            with (
                patch(
                    "application.database.index_document_data",
                    side_effect=(RuntimeError("forced sync failure"), None),
                ) as index_document,
                self.assertLogs(level="ERROR"),
            ):
                db_session.commit()

            self.assertEqual(index_document.call_count, 2)
            self.assertEqual(
                [call.args[0] for call in index_document.call_args_list],
                sorted((first.dataset_id, second.dataset_id)),
            )
