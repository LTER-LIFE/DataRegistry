from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from application import search_index


class TestSearchIndex(unittest.TestCase):
    @patch.object(search_index, "es")
    def test_rebuild_uses_stable_ids_and_accepted_records_only(self, es):
        es.indices.exists.return_value = True
        # Lightweight protocol stubs keep this unit test independent of the ORM,
        # database, and Flask serialization context.
        accepted = SimpleNamespace(
            dataset_id=4,
            review_lifecycle=SimpleNamespace(status="accepted"),
            to_dict=Mock(return_value={"dataset_id": 4, "status": "accepted"}),
        )
        submitted = SimpleNamespace(
            dataset_id=5,
            review_lifecycle=SimpleNamespace(status="submitted"),
            to_dict=Mock(return_value={"dataset_id": 5, "status": "submitted"}),
        )

        results = search_index.rebuild_index([accepted, submitted])

        self.assertEqual(len(results), 1)
        es.index.assert_called_once_with(
            index=search_index.INDEX_NAME,
            id=4,
            document={"dataset_id": 4, "status": "accepted"},
        )
        submitted.to_dict.assert_not_called()

    def test_public_queries_always_filter_for_accepted_status(self):
        query = search_index.build_es_query({"keywords": "forest"})

        self.assertIn(
            {"term": {"status": "accepted"}},
            query["query"]["bool"]["filter"],
        )
