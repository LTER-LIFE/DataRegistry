from datetime import datetime
import json
import os
import subprocess
import sys
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

    def _run_preflight_cli(self):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.catalogue_migration_preflight",
                "--database-url",
                self.url.render_as_string(hide_password=False),
                "--json",
            ],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            check=False,
        )

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
                    sa.text(
                        'SELECT dataset.public_id, lifecycle.status '
                        'FROM "Dataset" dataset '
                        'JOIN "ReviewLifecycle" lifecycle '
                        'ON lifecycle.review_lifecycle_id = '
                        'dataset.review_lifecycle_id'
                    )
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
            dataset_columns = {
                row["name"]
                for row in sa.inspect(connection).get_columns("Dataset")
            }
            self.assertNotIn("status", dataset_columns)
            self.assertNotIn("submitted_at", dataset_columns)
            self.assertNotIn("accepted_at", dataset_columns)
            self.assertNotIn("review_comment", dataset_columns)
            self.assertNotIn("submitter_id", dataset_columns)
            self.assertIn("review_lifecycle_id", dataset_columns)
            self.assertIn("review_owner_type", dataset_columns)
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
                    'SELECT lifecycle.submitted_at, lifecycle.accepted_at, '
                    'dataset.modified, lifecycle.current_review_comment '
                    'FROM "Dataset" dataset '
                    'JOIN "ReviewLifecycle" lifecycle '
                    'ON lifecycle.review_lifecycle_id = '
                    'dataset.review_lifecycle_id '
                    "WHERE dataset.public_id = 'rejected-id'"
                )
            ).one()
            self.assertIsNotNone(rejected_workflow[0])
            self.assertIsNone(rejected_workflow[1])
            self.assertEqual(rejected_workflow[2], datetime(2025, 1, 3))
            self.assertEqual(
                rejected_workflow[3], "Insufficient spatial description"
            )
            transitions = connection.execute(
                sa.text(
                    'SELECT dataset.public_id, transition.from_status, '
                    'transition.to_status, transition.review_comment, '
                    'transition.actor_id, transition.actor_mode '
                    'FROM "Dataset" dataset '
                    'JOIN "ReviewLifecycle" lifecycle '
                    'ON lifecycle.review_lifecycle_id = '
                    'dataset.review_lifecycle_id '
                    'JOIN "ReviewTransition" transition '
                    'ON transition.review_lifecycle_id = '
                    'lifecycle.review_lifecycle_id '
                    'ORDER BY dataset.public_id'
                )
            ).all()
            self.assertEqual(len(transitions), 4)
            for transition in transitions:
                with self.subTest(public_id=transition[0]):
                    self.assertIsNone(transition[1])
                    self.assertIsNone(transition[4])
                    self.assertEqual(transition[5], "migration")
            transitions_by_public_id = {row[0]: row for row in transitions}
            self.assertEqual(
                transitions_by_public_id["rejected-id"][3],
                "Insufficient spatial description",
            )
            self.assertEqual(
                transitions_by_public_id["resubmitted-id"][3],
                "Previous feedback",
            )

    def test_database_enforces_audit_ownership_and_aggregate_deletion(self):
        canonical = self.dataset_values("Cascade dataset", "cascade-id")
        with self.engine.begin() as connection:
            dataset_id = self._insert_dataset(connection, "Dataset", canonical)
            keyword_id = connection.execute(
                sa.text(
                    'INSERT INTO "Keyword" (name, slug) '
                    "VALUES ('cascade', 'cascade') RETURNING keyword_id"
                )
            ).scalar_one()
            theme_id = connection.execute(
                sa.text(
                    'INSERT INTO "DataTheme" (code, label) '
                    "VALUES ('cascade', 'Cascade theme') RETURNING data_theme_id"
                )
            ).scalar_one()
            connection.execute(
                sa.text(
                    'INSERT INTO "datasetKeyword" (keyword_id, dataset_id) '
                    "VALUES (:keyword_id, :dataset_id)"
                ),
                {"keyword_id": keyword_id, "dataset_id": dataset_id},
            )
            connection.execute(
                sa.text(
                    'INSERT INTO "datasetDataTheme" '
                    "(data_theme_id, dataset_id) "
                    "VALUES (:theme_id, :dataset_id)"
                ),
                {"theme_id": theme_id, "dataset_id": dataset_id},
            )
            connection.execute(
                sa.text(
                    'INSERT INTO "Distribution" '
                    "(distribution_dataset_id, title) "
                    "VALUES (:dataset_id, 'Cascade distribution')"
                ),
                {"dataset_id": dataset_id},
            )

        self._upgrade("head")

        with self.engine.connect() as connection:
            lifecycle_id, transition_id = connection.execute(
                sa.text(
                    'SELECT lifecycle.review_lifecycle_id, '
                    'transition.review_transition_id '
                    'FROM "Dataset" dataset '
                    'JOIN "ReviewLifecycle" lifecycle '
                    'ON lifecycle.review_lifecycle_id = '
                    'dataset.review_lifecycle_id '
                    'JOIN "ReviewTransition" transition '
                    'ON transition.review_lifecycle_id = '
                    'lifecycle.review_lifecycle_id '
                    "WHERE dataset.public_id = 'cascade-id'"
                )
            ).one()

        owner_first_lifecycle_id = 1_000_000
        with self.engine.begin() as connection:
            self._insert_dataset(
                connection,
                "Dataset",
                self.dataset_values("Owner-first dataset", "owner-first-id"),
                review_lifecycle_id=owner_first_lifecycle_id,
                review_owner_type="dataset",
            )
            connection.execute(
                sa.text(
                    'INSERT INTO "ReviewLifecycle" '
                    "(review_lifecycle_id, owner_type, status, submitted_at) "
                    "VALUES (:lifecycle_id, 'dataset', 'submitted', "
                    "CURRENT_TIMESTAMP)"
                ),
                {"lifecycle_id": owner_first_lifecycle_id},
            )
            connection.execute(
                sa.text(
                    'INSERT INTO "ReviewTransition" '
                    "(review_lifecycle_id, from_status, to_status, changed_at, "
                    "actor_mode) VALUES (:lifecycle_id, NULL, 'submitted', "
                    "CURRENT_TIMESTAMP, 'system')"
                ),
                {"lifecycle_id": owner_first_lifecycle_id},
            )
            connection.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))

        with self.assertRaises(sa.exc.IntegrityError) as orphan_error:
            with self.engine.begin() as connection:
                connection.execute(
                    sa.text(
                        'INSERT INTO "ReviewLifecycle" '
                        "(owner_type, status, submitted_at) "
                        "VALUES ('dataset', 'submitted', CURRENT_TIMESTAMP)"
                    )
                )
                connection.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))
        self.assertEqual(
            orphan_error.exception.orig.diag.constraint_name,
            "ck_ReviewLifecycle_exactly_one_owner",
        )

        with self.assertRaises(sa.exc.DBAPIError) as update_error:
            with self.engine.begin() as connection:
                connection.execute(
                    sa.text(
                        'UPDATE "ReviewTransition" '
                        "SET changed_at = changed_at + INTERVAL '1 second' "
                        "WHERE review_transition_id = :transition_id"
                    ),
                    {"transition_id": transition_id},
                )
        self.assertIn("Review transitions are immutable", str(update_error.exception.orig))

        with self.assertRaises(sa.exc.DBAPIError) as delete_error:
            with self.engine.begin() as connection:
                connection.execute(
                    sa.text(
                        'DELETE FROM "ReviewTransition" '
                        "WHERE review_transition_id = :transition_id"
                    ),
                    {"transition_id": transition_id},
                )
        self.assertIn(
            "Review transitions cannot be deleted directly",
            str(delete_error.exception.orig),
        )

        with self.assertRaises(sa.exc.IntegrityError) as owner_error:
            with self.engine.begin() as connection:
                connection.execute(
                    sa.text(
                        'DELETE FROM "Dataset" WHERE dataset_id = :dataset_id'
                    ),
                    {"dataset_id": dataset_id},
                )
                connection.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))
        self.assertEqual(
            owner_error.exception.orig.diag.constraint_name,
            "ck_ReviewLifecycle_exactly_one_owner",
        )

        with self.engine.begin() as connection:
            connection.execute(
                sa.text(
                    'DELETE FROM "ReviewLifecycle" '
                    "WHERE review_lifecycle_id = :lifecycle_id"
                ),
                {"lifecycle_id": lifecycle_id},
            )

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(
                    sa.text(
                        'SELECT COUNT(*) FROM "Dataset" '
                        "WHERE dataset_id = :dataset_id"
                    ),
                    {"dataset_id": dataset_id},
                ).scalar_one(),
                0,
            )
            self.assertEqual(
                connection.execute(
                    sa.text(
                        'SELECT COUNT(*) FROM "datasetDataTheme" '
                        "WHERE dataset_id = :dataset_id"
                    ),
                    {"dataset_id": dataset_id},
                ).scalar_one(),
                0,
            )
            self.assertEqual(
                connection.execute(
                    sa.text(
                        'SELECT COUNT(*) FROM "ReviewTransition" '
                        "WHERE review_lifecycle_id = :lifecycle_id"
                    ),
                    {"lifecycle_id": lifecycle_id},
                ).scalar_one(),
                0,
            )
            self.assertEqual(
                connection.execute(
                    sa.text(
                        'SELECT COUNT(*) FROM "Distribution" '
                        "WHERE distribution_dataset_id = :dataset_id"
                    ),
                    {"dataset_id": dataset_id},
                ).scalar_one(),
                0,
            )
            self.assertEqual(
                connection.execute(
                    sa.text(
                        'SELECT COUNT(*) FROM "datasetKeyword" '
                        "WHERE dataset_id = :dataset_id"
                    ),
                    {"dataset_id": dataset_id},
                ).scalar_one(),
                0,
            )

    def test_preflight_cli_reports_ready_and_blocked_exit_codes(self):
        ready = self._run_preflight_cli()

        self.assertEqual(ready.returncode, 0, ready.stderr)
        ready_report = json.loads(ready.stdout)
        self.assertTrue(ready_report["ready"])
        self.assertEqual(
            ready_report["database"]["alembic_revision"], "251acb193b99"
        )

        with self.engine.begin() as connection:
            connection.execute(
                sa.text(
                    'INSERT INTO "CatalogStaging" (title) '
                    "VALUES ('Unsupported catalogue')"
                )
            )

        blocked = self._run_preflight_cli()

        self.assertEqual(blocked.returncode, 1, blocked.stderr)
        blocked_report = json.loads(blocked.stdout)
        self.assertFalse(blocked_report["ready"])
        self.assertTrue(
            any("CatalogStaging contains 1" in item for item in blocked_report["blockers"])
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
            self.assertNotIn("review_lifecycle_id", columns)
            self.assertFalse(sa.inspect(connection).has_table("ReviewLifecycle"))

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
