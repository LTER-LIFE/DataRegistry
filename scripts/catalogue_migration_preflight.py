"""Read-only preflight checks for the single-catalogue migration."""

import argparse
from collections import Counter
import json
import os
import sys
from urllib.parse import quote_plus

import sqlalchemy as sa


EXPECTED_REVISION = "251acb193b99"
DATASET_FIELDS = (
    "release_date",
    "language",
    "title",
    "description",
    "resource_type",
    "temporal_coverage_start",
    "temporal_coverage_end",
    "temporal_resolution",
    "spatial_resolution",
    "access_rights",
    "modified",
    "taxonomic_coverage",
    "landing_page",
    "public_id",
)
UNSUPPORTED_TABLES = (
    "CatalogStaging",
    "DataThemeStaging",
    "DistributionStaging",
    "ChecksumStaging",
    "MediaTypeStaging",
    "DataServiceStaging",
    "datasetDataThemeStaging",
    "dataThemeCatalogStaging",
    "dataserviceMediaTypeStaging",
)


def database_url(explicit_url=None):
    if explicit_url:
        return explicit_url
    required = ("DB_USER", "DB_PWD", "DB_HOST", "DB_NAME")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Missing database settings: {', '.join(missing)}")
    return (
        f"postgresql://{quote_plus(os.environ['DB_USER'])}:"
        f"{quote_plus(os.environ['DB_PWD'])}@{os.environ['DB_HOST']}/"
        f"{quote_plus(os.environ['DB_NAME'])}"
    )


def _signature(row):
    return tuple(row[field] for field in DATASET_FIELDS)


def _sample_ids(connection, where_clause):
    return list(
        connection.execute(
            sa.text(
                'SELECT dataset_id FROM "DatasetStaging" '
                f"WHERE {where_clause} ORDER BY dataset_id LIMIT 10"
            )
        ).scalars()
    )


def inspect_catalogue(connection):
    report = {"blockers": [], "warnings": []}
    report["database"] = {
        "postgresql": connection.execute(sa.text("SELECT version()" )).scalar_one(),
        "postgis": connection.execute(
            sa.text("SELECT PostGIS_Full_Version()")
        ).scalar_one(),
        "alembic_revision": connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one(),
    }
    if report["database"]["alembic_revision"] != EXPECTED_REVISION:
        report["blockers"].append(
            f"Expected Alembic revision {EXPECTED_REVISION}, found "
            f"{report['database']['alembic_revision']}"
        )

    report["datasets"] = {
        "main": connection.execute(
            sa.text('SELECT COUNT(*) FROM "Dataset"')
        ).scalar_one(),
        "staging": connection.execute(
            sa.text('SELECT COUNT(*) FROM "DatasetStaging"')
        ).scalar_one(),
        "approved": connection.execute(
            sa.text(
                'SELECT COUNT(*) FROM "DatasetStaging" WHERE is_approved IS TRUE'
            )
        ).scalar_one(),
        "pending": connection.execute(
            sa.text(
                'SELECT COUNT(*) FROM "DatasetStaging" '
                "WHERE is_approved IS NOT TRUE "
                "AND (is_rejected IS NOT TRUE OR resubmitted_at IS NOT NULL)"
            )
        ).scalar_one(),
        "rejected": connection.execute(
            sa.text(
                'SELECT COUNT(*) FROM "DatasetStaging" '
                "WHERE is_rejected IS TRUE AND resubmitted_at IS NULL"
            )
        ).scalar_one(),
    }

    lifecycle_checks = {
        "approved_and_rejected": "is_approved IS TRUE AND is_rejected IS TRUE",
        "invalid_approval_timestamp": "(is_approved IS TRUE AND approved_at IS NULL) OR "
        "(is_approved IS NOT TRUE AND approved_at IS NOT NULL)",
        "rejected_without_comment": "is_rejected IS TRUE AND "
        "resubmitted_at IS NULL AND "
        "NULLIF(BTRIM(rejection_reason), '') IS NULL",
        "catalogue_reference": "dataset_catalog_id IS NOT NULL",
    }
    report["lifecycle"] = {}
    for name, condition in lifecycle_checks.items():
        ids = _sample_ids(connection, condition)
        report["lifecycle"][name] = ids
        if ids:
            report["blockers"].append(f"{name}: staging IDs {ids}")

    identifier_conflicts = list(
        connection.execute(
            sa.text(
                'SELECT DISTINCT staging.dataset_id FROM "DatasetStaging" staging '
                'JOIN "Dataset" canonical ON canonical.public_id = staging.public_id '
                "WHERE staging.is_approved IS NOT TRUE "
                "AND NULLIF(BTRIM(staging.public_id), '') IS NOT NULL "
                "ORDER BY staging.dataset_id LIMIT 10"
            )
        ).scalars()
    )
    report["lifecycle"]["public_id_conflict"] = identifier_conflicts
    if identifier_conflicts:
        report["blockers"].append(
            f"public_id_conflict: staging IDs {identifier_conflicts}"
        )

    invalid_geometries = list(
        connection.execute(
            sa.text(
                'SELECT staging.dataset_id FROM "DatasetStaging" staging '
                'JOIN "LocationStaging" location '
                "ON location.location_id = staging.dataset_spatial_coverage_id "
                "WHERE staging.is_approved IS NOT TRUE "
                "AND NOT ST_IsValid(location.geometry) "
                "ORDER BY staging.dataset_id LIMIT 10"
            )
        ).scalars()
    )
    report["lifecycle"]["invalid_geometry"] = invalid_geometries
    if invalid_geometries:
        report["blockers"].append(
            f"invalid_geometry: staging IDs {invalid_geometries}"
        )

    report["unsupported_staging_tables"] = {}
    for table_name in UNSUPPORTED_TABLES:
        count = connection.execute(
            sa.text(f'SELECT COUNT(*) FROM "{table_name}"')
        ).scalar_one()
        report["unsupported_staging_tables"][table_name] = count
        if count:
            report["blockers"].append(
                f"{table_name} contains {count} unsupported row(s)"
            )

    main_rows = connection.execute(
        sa.text(
            f'SELECT dataset_id, {", ".join(DATASET_FIELDS)} FROM "Dataset"'
        )
    ).mappings()
    main_signatures = Counter(_signature(row) for row in main_rows)
    approved_rows = connection.execute(
        sa.text(
            f'SELECT dataset_id, {", ".join(DATASET_FIELDS)} '
            'FROM "DatasetStaging" WHERE is_approved IS TRUE'
        )
    ).mappings()
    approved_matches = []
    claimed = Counter()
    for row in approved_rows:
        signature = _signature(row)
        matches = main_signatures[signature]
        approved_matches.append(
            {"staging_dataset_id": row["dataset_id"], "canonical_matches": matches}
        )
        claimed[signature] += 1
        if matches != 1:
            report["blockers"].append(
                f"approved staging dataset {row['dataset_id']} has {matches} "
                "exact canonical matches"
            )
    if any(count > 1 and main_signatures[sig] == 1 for sig, count in claimed.items()):
        report["blockers"].append(
            "Multiple approved staging rows claim one canonical dataset"
        )
    report["approved_reconciliation"] = approved_matches

    referenced = {}
    reference_checks = {
        "AgentStaging": (
            'SELECT COUNT(DISTINCT id) FROM (SELECT creator_id AS id FROM "DatasetStaging" '
            'UNION SELECT dataset_contact_point_id FROM "DatasetStaging" '
            'UNION SELECT dataset_publisher_id FROM "DatasetStaging" '
            'UNION SELECT dataset_metadata_provider_id FROM "DatasetStaging") refs '
            "WHERE id IS NOT NULL"
        ),
        "KeywordStaging": (
            'SELECT COUNT(DISTINCT keyword_id) FROM "datasetKeywordStaging"'
        ),
        "LocationStaging": (
            'SELECT COUNT(DISTINCT dataset_spatial_coverage_id) FROM "DatasetStaging" '
            "WHERE dataset_spatial_coverage_id IS NOT NULL"
        ),
        "LicenseDocumentStaging": (
            'SELECT COUNT(DISTINCT dataset_license_id) FROM "DatasetStaging" '
            "WHERE dataset_license_id IS NOT NULL"
        ),
    }
    for table_name, query in reference_checks.items():
        total = connection.execute(
            sa.text(f'SELECT COUNT(*) FROM "{table_name}"')
        ).scalar_one()
        used = connection.execute(sa.text(query)).scalar_one()
        referenced[table_name] = {"total": total, "referenced": used, "orphaned": total - used}
        if total > used:
            report["warnings"].append(
                f"{table_name} has {total - used} unreferenced helper row(s); "
                "they will remain only in the legacy tables"
            )
    report["supported_staging_entities"] = referenced
    report["ready"] = not report["blockers"]
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    try:
        engine = sa.create_engine(database_url(args.database_url), pool_pre_ping=True)
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            with connection.begin():
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                report = inspect_catalogue(connection)
    except (ValueError, sa.exc.SQLAlchemyError) as exc:
        print(f"Preflight could not inspect the database: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"Alembic revision: {report['database']['alembic_revision']}")
        print(
            "Datasets: "
            f"{report['datasets']['main']} main, "
            f"{report['datasets']['staging']} staging "
            f"({report['datasets']['approved']} approved, "
            f"{report['datasets']['pending']} pending, "
            f"{report['datasets']['rejected']} rejected)"
        )
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        for blocker in report["blockers"]:
            print(f"BLOCKER: {blocker}")
        print("READY" if report["ready"] else "BLOCKED")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
