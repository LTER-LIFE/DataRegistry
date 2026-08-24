from datetime import datetime
import os
import unittest

from alembic import command
from alembic.config import Config as AlembicConfig
import sqlalchemy as sa
from sqlalchemy_utils import create_database, database_exists, drop_database

from config import Config
from scripts.catalogue_migration_preflight import inspect_catalogue


class TestDatasetLifecycleMigration(unittest.TestCase):
    database_name = "ecosearchengine_migration_test"

    @classmethod
    def setUpClass(cls):
        cls.url = sa.engine.URL.create(
            "postgresql+psycopg2",
            username=Config.DB_USER,
            password=Config.DB_PWD,
            host=Config.DB_HOST,
            database=cls.database_name,
        )
        if database_exists(cls.url):
            drop_database(cls.url)
        create_database(cls.url)
        cls.engine = sa.create_engine(cls.url)
        with cls.engine.begin() as connection:
            connection.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        if database_exists(cls.url):
            drop_database(cls.url)

    def setUp(self):
        with self.engine.begin() as connection:
            connection.execute(sa.text("DROP SCHEMA public CASCADE"))
            connection.execute(sa.text("CREATE SCHEMA public"))
            connection.execute(sa.text("CREATE EXTENSION postgis"))
        self.alembic = AlembicConfig(os.path.join(os.getcwd(), "alembic.ini"))
        self._upgrade("251acb193b99")

    def _upgrade(self, revision):
        with self.engine.begin() as connection:
            self.alembic.attributes["connection"] = connection
            command.upgrade(self.alembic, revision)
        self.alembic.attributes.pop("connection", None)

    @staticmethod
    def dataset_values(title, public_id):
        timestamp = datetime(2025, 1, 1, 12, 0)
        return {
            "release_date": timestamp,
            "language": "EN",
            "title": title,
            "description": "Ecological metadata",
            "resource_type": "dataset",
            "temporal_coverage_start": datetime(2020, 1, 1),
            "temporal_coverage_end": datetime(2021, 1, 1),
            "temporal_resolution": "P1D",
            "spatial_resolution": None,
            "access_rights": "open access",
            "modified": timestamp,
            "taxonomic_coverage": "Plants",
            "landing_page": "https://example.org",
            "public_id": public_id,
        }

    def _insert_dataset(self, connection, table, values, **extra):
        all_values = dict(values, **extra)
        columns = ", ".join(f'"{name}"' for name in all_values)
        parameters = ", ".join(f":{name}" for name in all_values)
        return connection.execute(
            sa.text(
                f'INSERT INTO "{table}" ({columns}) VALUES ({parameters}) '
                "RETURNING dataset_id"
            ),
            all_values,
        ).scalar_one()

    def test_preflight_and_upgrade_preserve_staging_and_map_statuses(self):
        accepted = self.dataset_values("Accepted dataset", "accepted-id")
        pending = self.dataset_values("Pending dataset", "pending-id")
        rejected = self.dataset_values("Rejected dataset", "rejected-id")
        resubmitted = self.dataset_values("Resubmitted dataset", "resubmitted-id")
        with self.engine.begin() as connection:
            agent_id = connection.execute(
                sa.text(
                    'INSERT INTO "AgentStaging" (name, type, mbox) '
                    "VALUES ('Ecology Institute', 'Organisation', 'data@example.org') "
                    "RETURNING agent_id"
                )
            ).scalar_one()
            keyword_id = connection.execute(
                sa.text(
                    'INSERT INTO "KeywordStaging" (name, slug) '
                    "VALUES ('ecology', 'ecology') RETURNING keyword_id"
                )
            ).scalar_one()
            license_id = connection.execute(
                sa.text(
                    'INSERT INTO "LicenseDocumentStaging" (code, label) '
                    "VALUES ('CC-BY-4.0', 'Creative Commons Attribution') "
                    "RETURNING license_document_id"
                )
            ).scalar_one()
            location_id = connection.execute(
                sa.text(
                    'INSERT INTO "LocationStaging" (geometry, bbox, centroid) '
                    "VALUES ("
                    "ST_GeomFromText('GEOMETRYCOLLECTION(POINT(5 52))'), "
                    "ST_GeomFromText('POLYGON((5 52, 6 52, 6 53, 5 53, 5 52))'), "
                    "ST_GeomFromText('POINT(5.5 52.5)')) RETURNING location_id"
                )
            ).scalar_one()
            self._insert_dataset(connection, "Dataset", accepted)
            self._insert_dataset(
                connection,
                "DatasetStaging",
                accepted,
                is_approved=True,
                approved_at=datetime(2025, 1, 2),
                is_rejected=False,
            )
            pending_id = self._insert_dataset(
                connection,
                "DatasetStaging",
                pending,
                is_approved=False,
                is_rejected=False,
                creator_id=agent_id,
                dataset_contact_point_id=agent_id,
                dataset_metadata_provider_id=agent_id,
                dataset_spatial_coverage_id=location_id,
                dataset_license_id=license_id,
            )
            connection.execute(
                sa.text(
                    'INSERT INTO "datasetKeywordStaging" (keyword_id, dataset_id) '
                    "VALUES (:keyword_id, :dataset_id)"
                ),
                {"keyword_id": keyword_id, "dataset_id": pending_id},
            )
            self._insert_dataset(
                connection,
                "DatasetStaging",
                rejected,
                is_approved=False,
                is_rejected=True,
                rejection_reason="Insufficient spatial description",
                rejected_at=datetime(2025, 1, 3),
            )
            self._insert_dataset(
                connection,
                "DatasetStaging",
                resubmitted,
                is_approved=False,
                is_rejected=True,
                rejection_reason="Previous feedback",
                rejected_at=datetime(2025, 1, 3),
                resubmitted_at=datetime(2025, 1, 4),
            )

        with self.engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            with connection.begin():
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                report = inspect_catalogue(connection)
        self.assertTrue(report["ready"], report["blockers"])

        self._upgrade("head")

        with self.engine.connect() as connection:
            statuses = dict(
                connection.execute(
                    sa.text('SELECT public_id, status FROM "Dataset"')
                ).all()
            )
            self.assertEqual(
                statuses,
                {
                    "accepted-id": "accepted",
                    "pending-id": "submitted",
                    "rejected-id": "rejected",
                    "resubmitted-id": "submitted",
                },
            )
            self.assertEqual(
                connection.execute(
                    sa.text('SELECT COUNT(*) FROM "DatasetStaging"')
                ).scalar_one(),
                4,
            )
            migrated_relations = connection.execute(
                sa.text(
                    'SELECT creator_id, dataset_contact_point_id, '
                    'dataset_metadata_provider_id, dataset_spatial_coverage_id, '
                    'dataset_license_id FROM "Dataset" WHERE public_id = \'pending-id\''
                )
            ).one()
            self.assertTrue(all(value is not None for value in migrated_relations))
            self.assertEqual(
                connection.execute(
                    sa.text(
                        'SELECT keyword.name FROM "Keyword" keyword '
                        'JOIN "datasetKeyword" link ON link.keyword_id = keyword.keyword_id '
                        'JOIN "Dataset" dataset ON dataset.dataset_id = link.dataset_id '
                        "WHERE dataset.public_id = 'pending-id'"
                    )
                ).scalar_one(),
                "ecology",
            )
            copied_values = connection.execute(
                sa.text(
                    'SELECT agent.name, license.code, ST_AsText(location.geometry) '
                    'FROM "Dataset" dataset '
                    'JOIN "Agent" agent ON agent.agent_id = dataset.creator_id '
                    'JOIN "LicenseDocument" license '
                    'ON license.license_document_id = dataset.dataset_license_id '
                    'JOIN "Location" location '
                    'ON location.location_id = dataset.dataset_spatial_coverage_id '
                    "WHERE dataset.public_id = 'pending-id'"
                )
            ).one()
            self.assertEqual(copied_values[0], "Ecology Institute")
            self.assertEqual(copied_values[1], "CC-BY-4.0")
            self.assertEqual(
                copied_values[2], "GEOMETRYCOLLECTION(POINT(5 52))"
            )
            rejected_workflow = connection.execute(
                sa.text(
                    'SELECT submitted_at, accepted_at, modified, review_comment '
                    'FROM "Dataset" WHERE public_id = \'rejected-id\''
                )
            ).one()
            self.assertIsNotNone(rejected_workflow[0])
            self.assertIsNone(rejected_workflow[1])
            self.assertEqual(rejected_workflow[2], datetime(2025, 1, 3))
            self.assertEqual(
                rejected_workflow[3], "Insufficient spatial description"
            )

    def test_unsupported_staging_data_blocks_upgrade_atomically(self):
        with self.engine.begin() as connection:
            connection.execute(
                sa.text(
                    'INSERT INTO "CatalogStaging" (title) VALUES (\'Legacy catalogue\')'
                )
            )

        with self.assertRaisesRegex(Exception, "CatalogStaging contains 1"):
            self._upgrade("head")

        with self.engine.connect() as connection:
            columns = {
                row["name"]
                for row in sa.inspect(connection).get_columns("Dataset")
            }
            self.assertNotIn("status", columns)

    def test_unmatched_approved_record_is_reported_and_blocks_upgrade(self):
        approved = self.dataset_values("Unmatched approved", "unmatched-id")
        with self.engine.begin() as connection:
            self._insert_dataset(
                connection,
                "DatasetStaging",
                approved,
                is_approved=True,
                approved_at=datetime(2025, 1, 2),
                is_rejected=False,
            )

        with self.engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            with connection.begin():
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                report = inspect_catalogue(connection)
        self.assertFalse(report["ready"])
        self.assertTrue(
            any("has 0 exact canonical matches" in item for item in report["blockers"])
        )

        with self.assertRaisesRegex(Exception, "0 exact canonical matches"):
            self._upgrade("head")
