from datetime import datetime
import unittest
from unittest.mock import call, Mock, patch

from application.database import db_session
from application.models import Dataset
from test.db import engine
from test.mock_objects import MockObjects


class TestMockObjects(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        db_session.configure(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )
        self.mock_objects = MockObjects(db_session=db_session)

    def tearDown(self):
        db_session.remove()
        self.transaction.rollback()
        self.connection.close()

    def test_default_dataset_is_complete_accepted_and_persisted(self):
        dataset = self.mock_objects.create_mock_dataset("default")

        self.assertIs(db_session.get(Dataset, dataset.dataset_id), dataset)
        self.assertEqual(dataset.title, "Mock dataset - default")
        self.assertEqual(dataset.review_lifecycle.status, "accepted")
        self.assertEqual(len(dataset.review_lifecycle.transitions), 2)
        self.assertIsNotNone(dataset.creator)
        self.assertIsNotNone(dataset.dataset_spatial_coverage)
        self.assertEqual(len(dataset.dataset_keywords), 1)

    def test_factory_supports_every_review_status(self):
        expected_transition_counts = {
            "submitted": 1,
            "revision": 2,
            "rejected": 2,
            "accepted": 2,
        }

        for status, transition_count in expected_transition_counts.items():
            with self.subTest(status=status):
                dataset = self.mock_objects.create_mock_dataset(
                    status,
                    status=status,
                    include_related=False,
                )
                self.assertEqual(dataset.review_lifecycle.status, status)
                self.assertEqual(
                    len(dataset.review_lifecycle.transitions),
                    transition_count,
                )

    def test_transient_minimal_dataset_is_deterministic_and_uses_overrides(self):
        session = Mock()
        changed_at = datetime(2027, 2, 3, 4, 5)
        dataset = MockObjects(session).create_mock_dataset(
            "transient",
            status="submitted",
            persist=False,
            changed_at=changed_at,
            include_related=False,
            dataset_overrides={"title": "Overridden title"},
        )

        self.assertEqual(dataset.title, "Overridden title")
        self.assertEqual(dataset.modified, changed_at)
        self.assertEqual(dataset.review_lifecycle.submitted_at, changed_at)
        self.assertEqual(dataset.review_lifecycle.status, "submitted")
        self.assertIsNone(dataset.creator)
        self.assertEqual(dataset.dataset_keywords, [])
        session.add.assert_not_called()
        session.commit.assert_not_called()

    def test_commit_false_adds_without_completing_transaction(self):
        session = Mock()
        dataset = MockObjects(session).create_mock_dataset(
            "uncommitted",
            persist=True,
            commit=False,
            include_related=False,
        )

        session.add.assert_called_once_with(dataset)
        session.commit.assert_not_called()
        session.flush.assert_not_called()

    def test_fake_dataset_preserves_realistic_generation_path(self):
        session = Mock()
        dataset = MockObjects(session).create_fake_dataset(
            "realistic",
            persist=False,
        )

        self.assertTrue(dataset.title.endswith(" - realistic"))
        self.assertTrue(dataset.public_id.startswith("DS-realistic-"))
        self.assertEqual(dataset.review_lifecycle.status, "accepted")
        self.assertIsNotNone(dataset.creator)
        self.assertIsNotNone(dataset.dataset_spatial_coverage)
        self.assertGreaterEqual(len(dataset.dataset_keywords), 1)
        session.add.assert_not_called()
        session.commit.assert_not_called()

    def test_bulk_generation_uses_fake_dataset_path(self):
        mock_objects = MockObjects(Mock())
        generated = [Mock(title="First"), Mock(title="Second")]

        with (
            patch.object(
                mock_objects,
                "create_fake_dataset",
                side_effect=generated,
            ) as create_fake_dataset,
            patch("builtins.print"),
        ):
            result = mock_objects.generate_datasets(2, "bulk")

        self.assertEqual(result, generated)
        create_fake_dataset.assert_has_calls(
            [call("ds-bulk-1"), call("ds-bulk-2")]
        )

    def test_invalid_status_has_no_session_side_effects(self):
        session = Mock()

        with self.assertRaisesRegex(ValueError, "Unsupported fixture review status"):
            MockObjects(session).create_mock_dataset("invalid", status="draft")

        session.add.assert_not_called()
        session.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
