from unittest.mock import AsyncMock, patch

from application.database import db_session
from application.models import Agent, Dataset, Keyword, LicenseDocument, Location
from test.base_test_case import BaseTestCase
from test.db import engine


def submission_data():
    return {
        "metadata_provider_name": "Metadata Provider",
        "metadata_provider_organisation": "LTER",
        "metadata_provider_mbox": "provider@example.org",
        "creator_name": "",
        "creator_organisation": "Ecology Institute",
        "creator_mbox": "creator@example.org",
        "dataset_contact_point_name": "Data Steward",
        "dataset_contact_point_organisation": "Ecology Institute",
        "dataset_contact_point_mbox": "steward@example.org",
        "title": "A community ecology dataset",
        "description": "Metadata for a public ecological resource.",
        "keywords": "ecology,community",
        "resource_type": "observational data",
        "license": "CC-BY-4.0",
        "access_rights": "open access",
        "publisher": "",
        "public_id": "10.1234/example",
        "landing_page": "https://example.org/dataset",
        "temporal_coverage_start": "2020-01-01",
        "temporal_coverage_end": "2021-01-01",
        "temporal_resolution": "P1D",
        "spatial_coverage": "GEOMETRYCOLLECTION (POINT (5.5 52.0))",
        "spatial_resolution": "100 m",
        "taxonomic_coverage": "Plants",
        "release_date": "2026-08-20",
        "language": "EN",
        "consent": "Y",
        "submit_button": "Submit dataset",
    }


class TestDatasetSubmission(BaseTestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        db_session.configure(bind=self.connection, join_transaction_mode="create_savepoint")

    def tearDown(self):
        db_session.remove()
        self.transaction.rollback()
        self.connection.close()

    def test_manual_submission_creates_one_non_public_dataset(self):
        response = self.client.post("/stage_dataset", data=submission_data())

        self.assertEqual(response.status_code, 302)
        datasets = db_session.query(Dataset).all()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].status, "submitted")
        self.assertIsNotNone(datasets[0].submitted_at)
        self.assertIsNone(datasets[0].accepted_at)

    def test_invalid_submission_is_atomic(self):
        data = submission_data()
        data["title"] = ""

        response = self.client.post("/stage_dataset", data=data)

        self.assertEqual(response.status_code, 200)
        for model in (Dataset, Agent, Keyword, LicenseDocument, Location):
            self.assertEqual(db_session.query(model).count(), 0)

    @patch("application.routes.LlmMetadataService")
    def test_ai_result_only_prefills_the_manual_form(self, service_class):
        service_class.return_value.check_job = AsyncMock(
            return_value=(
                "success",
                {
                    "result": {
                        "Title": "AI suggested title",
                        "Description": "AI suggested description",
                        "Metadata date": "2026-08-20",
                        "Metadata language": "EN",
                        "Resource type": "dataset",
                        "Temporal coverage": "2020-01-01",
                        "Temporal resolution": "P1D",
                        "Access rights": "open access",
                    }
                },
            )
        )

        response = self.client.post("/dataset/from-ai", data={"job_id": "job-1"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'action="/stage_dataset"', response.data)
        self.assertIn(b"AI suggested title", response.data)
        for model in (Dataset, Agent, Keyword, LicenseDocument, Location):
            self.assertEqual(db_session.query(model).count(), 0)
