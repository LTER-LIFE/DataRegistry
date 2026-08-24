from datetime import datetime
import unittest

from application.models import Dataset
from application.workflow import transition_dataset


class TestDatasetWorkflow(unittest.TestCase):
    def dataset(self, status="submitted"):
        return Dataset(
            status=status,
            submitted_at=datetime(2026, 1, 1),
            modified=datetime(2026, 1, 1),
        )

    def test_accept_sets_acceptance_time_and_clears_comment(self):
        dataset = self.dataset()
        dataset.review_comment = "old feedback"
        changed_at = datetime(2026, 2, 1, 12, 30)

        transition_dataset(dataset, "accepted", changed_at=changed_at)

        self.assertEqual(dataset.status, "accepted")
        self.assertEqual(dataset.accepted_at, changed_at)
        self.assertEqual(dataset.modified, changed_at)
        self.assertIsNone(dataset.review_comment)

    def test_revision_requires_feedback(self):
        dataset = self.dataset()

        with self.assertRaisesRegex(ValueError, "require review feedback"):
            transition_dataset(dataset, "revision")

    def test_accepted_record_can_return_to_revision(self):
        dataset = self.dataset("accepted")
        dataset.accepted_at = datetime(2026, 1, 2)

        transition_dataset(dataset, "revision", "Please clarify the location.")

        self.assertEqual(dataset.status, "revision")
        self.assertEqual(dataset.review_comment, "Please clarify the location.")
        self.assertEqual(dataset.accepted_at, datetime(2026, 1, 2))

    def test_rejected_record_can_be_reopened(self):
        dataset = self.dataset("rejected")
        dataset.review_comment = "Original rejection"

        transition_dataset(dataset, "revision", "Reopened after follow-up.")

        self.assertEqual(dataset.status, "revision")

    def test_revision_must_be_resubmitted_before_acceptance(self):
        dataset = self.dataset("revision")

        with self.assertRaisesRegex(ValueError, "Cannot transition"):
            transition_dataset(dataset, "accepted")
