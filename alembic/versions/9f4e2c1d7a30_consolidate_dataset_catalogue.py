"""Consolidate submitted datasets into the canonical catalogue.

Revision ID: 9f4e2c1d7a30
Revises: 251acb193b99
Create Date: 2026-08-20

The legacy staging tables deliberately remain in place as a read-only archive.
They can be removed by a later migration after the migrated records have been
verified in acceptance and production.
"""

from collections import Counter
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f4e2c1d7a30"
down_revision: Union[str, None] = "251acb193b99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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

UNSUPPORTED_STAGING_TABLES = (
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


def _signature(row):
    return tuple(row[field] for field in DATASET_FIELDS)


def _ids(connection, query, parameters=None):
    return list(connection.execute(sa.text(query), parameters or {}).scalars())


def _validate_source(connection):
    blockers = []

    contradictory = _ids(
        connection,
        'SELECT dataset_id FROM "DatasetStaging" '
        "WHERE is_approved IS TRUE AND is_rejected IS TRUE",
    )
    if contradictory:
        blockers.append(f"approved and rejected staging datasets: {contradictory[:10]}")

    invalid_approval_dates = _ids(
        connection,
        'SELECT dataset_id FROM "DatasetStaging" '
        "WHERE (is_approved IS TRUE AND approved_at IS NULL) "
        "OR (is_approved IS NOT TRUE AND approved_at IS NOT NULL)",
    )
    if invalid_approval_dates:
        blockers.append(
            "staging datasets with inconsistent approval timestamps: "
            f"{invalid_approval_dates[:10]}"
        )

    rejected_without_comment = _ids(
        connection,
        'SELECT dataset_id FROM "DatasetStaging" '
        "WHERE is_rejected IS TRUE "
        "AND resubmitted_at IS NULL "
        "AND NULLIF(BTRIM(rejection_reason), '') IS NULL",
    )
    if rejected_without_comment:
        blockers.append(
            "rejected staging datasets without review feedback: "
            f"{rejected_without_comment[:10]}"
        )

    for table_name in UNSUPPORTED_STAGING_TABLES:
        count = connection.execute(
            sa.text(f'SELECT COUNT(*) FROM "{table_name}"')
        ).scalar_one()
        if count:
            blockers.append(f'{table_name} contains {count} unsupported row(s)')

    catalogued = _ids(
        connection,
        'SELECT dataset_id FROM "DatasetStaging" '
        "WHERE dataset_catalog_id IS NOT NULL",
    )
    if catalogued:
        blockers.append(
            f"staging datasets reference a staging catalogue: {catalogued[:10]}"
        )

    identifier_conflicts = _ids(
        connection,
        'SELECT DISTINCT staging.dataset_id FROM "DatasetStaging" staging '
        'JOIN "Dataset" canonical ON canonical.public_id = staging.public_id '
        "WHERE staging.is_approved IS NOT TRUE "
        "AND NULLIF(BTRIM(staging.public_id), '') IS NOT NULL",
    )
    if identifier_conflicts:
        blockers.append(
            "non-approved staging datasets reuse a canonical public_id: "
            f"{identifier_conflicts[:10]}"
        )

    invalid_geometries = _ids(
        connection,
        'SELECT staging.dataset_id FROM "DatasetStaging" staging '
        'JOIN "LocationStaging" location '
        "ON location.location_id = staging.dataset_spatial_coverage_id "
        "WHERE staging.is_approved IS NOT TRUE AND NOT ST_IsValid(location.geometry)",
    )
    if invalid_geometries:
        blockers.append(
            f"staging datasets contain invalid geometry: {invalid_geometries[:10]}"
        )

    main_rows = connection.execute(
        sa.text(
            f'SELECT dataset_id, {", ".join(DATASET_FIELDS)} FROM "Dataset"'
        )
    ).mappings()
    signature_counts = Counter(_signature(row) for row in main_rows)
    approved_rows = connection.execute(
        sa.text(
            f'SELECT dataset_id, {", ".join(DATASET_FIELDS)} '
            'FROM "DatasetStaging" WHERE is_approved IS TRUE'
        )
    ).mappings()

    claimed_signatures = Counter()
    for row in approved_rows:
        signature = _signature(row)
        matches = signature_counts[signature]
        if matches != 1:
            blockers.append(
                f"approved staging dataset {row['dataset_id']} has {matches} "
                "exact canonical matches"
            )
        claimed_signatures[signature] += 1

    duplicate_claims = [
        count for signature, count in claimed_signatures.items()
        if count > 1 and signature_counts[signature] == 1
    ]
    if duplicate_claims:
        blockers.append("multiple approved staging rows claim one canonical dataset")

    if blockers:
        details = "\n- ".join(blockers)
        raise RuntimeError(f"Catalogue consolidation preflight failed:\n- {details}")


def _copy_agent(connection, staging_id, mapping):
    if staging_id is None:
        return None
    if staging_id not in mapping:
        mapping[staging_id] = connection.execute(
            sa.text(
                'INSERT INTO "Agent" (name, type, mbox) '
                'SELECT name, type, mbox FROM "AgentStaging" '
                "WHERE agent_id = :source_id RETURNING agent_id"
            ),
            {"source_id": staging_id},
        ).scalar_one()
    return mapping[staging_id]


def _copy_keyword(connection, staging_id, mapping):
    if staging_id not in mapping:
        mapping[staging_id] = connection.execute(
            sa.text(
                'INSERT INTO "Keyword" (name, slug) '
                'SELECT name, slug FROM "KeywordStaging" '
                "WHERE keyword_id = :source_id RETURNING keyword_id"
            ),
            {"source_id": staging_id},
        ).scalar_one()
    return mapping[staging_id]


def _copy_license(connection, staging_id, mapping):
    if staging_id is None:
        return None
    if staging_id not in mapping:
        mapping[staging_id] = connection.execute(
            sa.text(
                'INSERT INTO "LicenseDocument" '
                "(label, code, url_general, url_document) "
                'SELECT label, code, url_general, url_document '
                'FROM "LicenseDocumentStaging" '
                "WHERE license_document_id = :source_id "
                "RETURNING license_document_id"
            ),
            {"source_id": staging_id},
        ).scalar_one()
    return mapping[staging_id]


def _copy_location(connection, staging_id, mapping):
    if staging_id is None:
        return None
    if staging_id not in mapping:
        mapping[staging_id] = connection.execute(
            sa.text(
                'INSERT INTO "Location" (bbox, centroid, geometry) '
                'SELECT bbox, centroid, geometry FROM "LocationStaging" '
                "WHERE location_id = :source_id RETURNING location_id"
            ),
            {"source_id": staging_id},
        ).scalar_one()
    return mapping[staging_id]


def _latest_change(row):
    values = [row["modified"], row["rejected_at"], row["resubmitted_at"]]
    return max(value for value in values if isinstance(value, datetime))


def _migrate_staging_datasets(connection, cutover_at):
    agent_mapping = {}
    keyword_mapping = {}
    license_mapping = {}
    location_mapping = {}

    staging_rows = connection.execute(
        sa.text(
            'SELECT * FROM "DatasetStaging" '
            "WHERE is_approved IS NOT TRUE ORDER BY dataset_id"
        )
    ).mappings().all()

    for row in staging_rows:
        creator_id = _copy_agent(connection, row["creator_id"], agent_mapping)
        contact_id = _copy_agent(
            connection, row["dataset_contact_point_id"], agent_mapping
        )
        publisher_id = _copy_agent(
            connection, row["dataset_publisher_id"], agent_mapping
        )
        provider_id = _copy_agent(
            connection, row["dataset_metadata_provider_id"], agent_mapping
        )
        location_id = _copy_location(
            connection, row["dataset_spatial_coverage_id"], location_mapping
        )
        license_id = _copy_license(
            connection, row["dataset_license_id"], license_mapping
        )

        status = (
            "rejected"
            if row["is_rejected"] is True and row["resubmitted_at"] is None
            else "submitted"
        )
        values = {field: row[field] for field in DATASET_FIELDS}
        values.update(
            {
                "creator_id": creator_id,
                "dataset_contact_point_id": contact_id,
                "dataset_publisher_id": publisher_id,
                "dataset_metadata_provider_id": provider_id,
                "dataset_spatial_coverage_id": location_id,
                "dataset_license_id": license_id,
                "dataset_catalog_id": None,
                "status": status,
                "submitted_at": cutover_at,
                "accepted_at": None,
                "review_comment": row["rejection_reason"],
                "submitter_id": None,
                "modified": _latest_change(row),
            }
        )

        columns = ", ".join(f'"{name}"' for name in values)
        parameters = ", ".join(f":{name}" for name in values)
        destination_id = connection.execute(
            sa.text(
                f'INSERT INTO "Dataset" ({columns}) VALUES ({parameters}) '
                "RETURNING dataset_id"
            ),
            values,
        ).scalar_one()

        staging_keyword_ids = _ids(
            connection,
            'SELECT keyword_id FROM "datasetKeywordStaging" '
            "WHERE dataset_id = :dataset_id ORDER BY keyword_id",
            {"dataset_id": row["dataset_id"]},
        )
        for staging_keyword_id in staging_keyword_ids:
            keyword_id = _copy_keyword(
                connection, staging_keyword_id, keyword_mapping
            )
            connection.execute(
                sa.text(
                    'INSERT INTO "datasetKeyword" (keyword_id, dataset_id) '
                    "VALUES (:keyword_id, :dataset_id)"
                ),
                {"keyword_id": keyword_id, "dataset_id": destination_id},
            )

    return len(staging_rows)


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Catalogue consolidation requires PostgreSQL/PostGIS")

    connection.execute(
        sa.text(
            'LOCK TABLE "Dataset", "DatasetStaging", "Agent", '
            '"AgentStaging", "Keyword", "KeywordStaging", '
            '"LicenseDocument", "LicenseDocumentStaging", "Location", '
            '"LocationStaging", "datasetKeyword", "datasetKeywordStaging", '
            '"CatalogStaging", "DataThemeStaging", "DistributionStaging", '
            '"ChecksumStaging", "MediaTypeStaging", "DataServiceStaging", '
            '"datasetDataThemeStaging", "dataThemeCatalogStaging", '
            '"dataserviceMediaTypeStaging" '
            "IN SHARE ROW EXCLUSIVE MODE"
        )
    )
    _validate_source(connection)

    original_main_count = connection.execute(
        sa.text('SELECT COUNT(*) FROM "Dataset"')
    ).scalar_one()
    cutover_at = connection.execute(
        sa.text("SELECT timezone('UTC', CURRENT_TIMESTAMP)")
    ).scalar_one()

    op.add_column(
        "Dataset",
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=True,
            server_default="submitted",
        ),
    )
    op.add_column("Dataset", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    op.add_column("Dataset", sa.Column("accepted_at", sa.DateTime(), nullable=True))
    op.add_column("Dataset", sa.Column("review_comment", sa.Text(), nullable=True))
    op.add_column("Dataset", sa.Column("submitter_id", sa.String(255), nullable=True))

    connection.execute(
        sa.text(
            'UPDATE "Dataset" SET status = \'accepted\', '
            "submitted_at = :cutover_at, accepted_at = :cutover_at"
        ),
        {"cutover_at": cutover_at},
    )
    migrated_count = _migrate_staging_datasets(connection, cutover_at)

    op.alter_column("Dataset", "status", nullable=False)
    op.alter_column("Dataset", "submitted_at", nullable=False)
    op.create_check_constraint(
        "ck_Dataset_status",
        "Dataset",
        "status IN ('submitted', 'revision', 'rejected', 'accepted')",
    )
    op.create_check_constraint(
        "ck_Dataset_accepted_at",
        "Dataset",
        "status <> 'accepted' OR accepted_at IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_Dataset_review_comment",
        "Dataset",
        "status NOT IN ('revision', 'rejected') "
        "OR NULLIF(BTRIM(review_comment), '') IS NOT NULL",
    )
    op.create_index("ix_Dataset_status", "Dataset", ["status"])
    op.create_index("ix_Dataset_submitter_id", "Dataset", ["submitter_id"])

    final_count = connection.execute(
        sa.text('SELECT COUNT(*) FROM "Dataset"')
    ).scalar_one()
    if final_count != original_main_count + migrated_count:
        raise RuntimeError(
            "Catalogue consolidation produced an unexpected Dataset row count"
        )


def downgrade() -> None:
    raise RuntimeError(
        "Catalogue consolidation is irreversible; restore the matching database "
        "backup and application release instead."
    )
