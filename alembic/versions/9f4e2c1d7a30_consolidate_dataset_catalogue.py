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


def _create_lifecycle_snapshot(
    connection,
    *,
    status,
    submitted_at,
    accepted_at=None,
    review_comment=None,
    submitter_id=None,
    changed_at,
):
    lifecycle_id = connection.execute(
        sa.text(
            'INSERT INTO "ReviewLifecycle" '
            "(owner_type, status, submitted_at, accepted_at, "
            "current_review_comment, submitter_id) "
            "VALUES ('dataset', :status, :submitted_at, :accepted_at, "
            ":review_comment, :submitter_id) RETURNING review_lifecycle_id"
        ),
        {
            "status": status,
            "submitted_at": submitted_at,
            "accepted_at": accepted_at,
            "review_comment": review_comment,
            "submitter_id": submitter_id,
        },
    ).scalar_one()
    connection.execute(
        sa.text(
            'INSERT INTO "ReviewTransition" '
            "(review_lifecycle_id, from_status, to_status, changed_at, "
            "review_comment, actor_id, actor_mode) "
            "VALUES (:lifecycle_id, NULL, :status, :changed_at, "
            ":review_comment, NULL, 'migration')"
        ),
        {
            "lifecycle_id": lifecycle_id,
            "status": status,
            "changed_at": changed_at,
            "review_comment": review_comment,
        },
    )
    return lifecycle_id


def _attach_canonical_lifecycles(connection, cutover_at):
    dataset_ids = _ids(
        connection,
        'SELECT dataset_id FROM "Dataset" ORDER BY dataset_id',
    )
    for dataset_id in dataset_ids:
        lifecycle_id = _create_lifecycle_snapshot(
            connection,
            status="accepted",
            submitted_at=cutover_at,
            accepted_at=cutover_at,
            changed_at=cutover_at,
        )
        connection.execute(
            sa.text(
                'UPDATE "Dataset" SET review_lifecycle_id = :lifecycle_id, '
                "review_owner_type = 'dataset' WHERE dataset_id = :dataset_id"
            ),
            {"lifecycle_id": lifecycle_id, "dataset_id": dataset_id},
        )


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
        review_comment = row["rejection_reason"]
        lifecycle_id = _create_lifecycle_snapshot(
            connection,
            status=status,
            submitted_at=cutover_at,
            review_comment=review_comment,
            changed_at=cutover_at,
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
                "review_lifecycle_id": lifecycle_id,
                "review_owner_type": "dataset",
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


def _create_review_tables():
    op.create_table(
        "ReviewLifecycle",
        sa.Column("review_lifecycle_id", sa.Integer(), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("current_review_comment", sa.Text(), nullable=True),
        sa.Column("submitter_id", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "owner_type IN ('dataset')",
            name="ck_ReviewLifecycle_owner_type",
        ),
        sa.CheckConstraint(
            "status IN ('submitted', 'revision', 'rejected', 'accepted')",
            name="ck_ReviewLifecycle_status",
        ),
        sa.CheckConstraint(
            "status <> 'accepted' OR accepted_at IS NOT NULL",
            name="ck_ReviewLifecycle_accepted_at",
        ),
        sa.CheckConstraint(
            "status NOT IN ('revision', 'rejected') "
            "OR NULLIF(BTRIM(current_review_comment), '') IS NOT NULL",
            name="ck_ReviewLifecycle_review_comment",
        ),
        sa.PrimaryKeyConstraint("review_lifecycle_id"),
        sa.UniqueConstraint(
            "review_lifecycle_id",
            "owner_type",
            name="uq_ReviewLifecycle_id_owner_type",
        ),
    )
    op.create_index(
        "ix_ReviewLifecycle_owner_type_status",
        "ReviewLifecycle",
        ["owner_type", "status"],
    )
    op.create_index(
        "ix_ReviewLifecycle_submitter_id",
        "ReviewLifecycle",
        ["submitter_id"],
    )

    op.create_table(
        "ReviewTransition",
        sa.Column("review_transition_id", sa.Integer(), nullable=False),
        sa.Column("review_lifecycle_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("actor_mode", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "from_status IS NULL "
            "OR from_status IN ('submitted', 'revision', 'rejected', 'accepted')",
            name="ck_ReviewTransition_from_status",
        ),
        sa.CheckConstraint(
            "to_status IN ('submitted', 'revision', 'rejected', 'accepted')",
            name="ck_ReviewTransition_to_status",
        ),
        sa.CheckConstraint(
            "to_status NOT IN ('revision', 'rejected') "
            "OR NULLIF(BTRIM(review_comment), '') IS NOT NULL",
            name="ck_ReviewTransition_review_comment",
        ),
        sa.CheckConstraint(
            "actor_mode IN "
            "('authenticated', 'anonymous', 'local_bypass', 'migration', 'system')",
            name="ck_ReviewTransition_actor_mode",
        ),
        sa.CheckConstraint(
            "(actor_mode = 'authenticated' "
            "AND NULLIF(BTRIM(actor_id), '') IS NOT NULL) "
            "OR (actor_mode <> 'authenticated' AND actor_id IS NULL)",
            name="ck_ReviewTransition_actor_identity",
        ),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status <> to_status",
            name="ck_ReviewTransition_state_change",
        ),
        sa.ForeignKeyConstraint(
            ["review_lifecycle_id"],
            ["ReviewLifecycle.review_lifecycle_id"],
            name="fk_ReviewTransition_lifecycle",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("review_transition_id"),
    )
    op.create_index(
        "ix_ReviewTransition_lifecycle_changed_at",
        "ReviewTransition",
        ["review_lifecycle_id", "changed_at"],
    )
    op.create_index(
        "ix_ReviewTransition_actor_id",
        "ReviewTransition",
        ["actor_id"],
    )


def _replace_dataset_foreign_key_with_cascade(connection, table_name, column_name):
    foreign_keys = sa.inspect(connection).get_foreign_keys(table_name)
    existing = next(
        foreign_key
        for foreign_key in foreign_keys
        if foreign_key["constrained_columns"] == [column_name]
        and foreign_key["referred_table"] == "Dataset"
    )
    op.drop_constraint(existing["name"], table_name, type_="foreignkey")
    op.create_foreign_key(
        f"fk_{table_name}_{column_name}",
        table_name,
        "Dataset",
        [column_name],
        ["dataset_id"],
        ondelete="CASCADE",
    )


def _create_review_triggers(connection):
    connection.execute(
        sa.text(
            """
            CREATE FUNCTION enforce_review_lifecycle_ownership()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                candidate_id integer;
                lifecycle_owner_type varchar;
                owner_count integer;
            BEGIN
                FOR candidate_id IN
                    SELECT DISTINCT lifecycle_id
                    FROM unnest(ARRAY[
                        CASE WHEN TG_OP <> 'DELETE'
                            THEN NEW.review_lifecycle_id END,
                        CASE WHEN TG_OP <> 'INSERT'
                            THEN OLD.review_lifecycle_id END
                    ]) AS affected(lifecycle_id)
                    WHERE lifecycle_id IS NOT NULL
                LOOP
                    SELECT owner_type
                    INTO lifecycle_owner_type
                    FROM "ReviewLifecycle"
                    WHERE review_lifecycle_id = candidate_id;

                    IF NOT FOUND THEN
                        CONTINUE;
                    END IF;

                    IF lifecycle_owner_type = 'dataset' THEN
                        SELECT COUNT(*)
                        INTO owner_count
                        FROM "Dataset"
                        WHERE review_lifecycle_id = candidate_id
                            AND review_owner_type = lifecycle_owner_type;
                    ELSE
                        RAISE EXCEPTION
                            'Unsupported review lifecycle owner type %',
                            lifecycle_owner_type
                            USING ERRCODE = '23514',
                                CONSTRAINT = 'ck_ReviewLifecycle_exactly_one_owner';
                    END IF;

                    IF owner_count <> 1 THEN
                        RAISE EXCEPTION
                            'Review lifecycle % must have exactly one % owner; found %',
                            candidate_id,
                            lifecycle_owner_type,
                            owner_count
                            USING ERRCODE = '23514',
                                CONSTRAINT = 'ck_ReviewLifecycle_exactly_one_owner';
                    END IF;
                END LOOP;

                RETURN NULL;
            END;
            $$
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE CONSTRAINT TRIGGER "ct_ReviewLifecycle_exactly_one_owner"
            AFTER INSERT OR UPDATE OR DELETE ON "ReviewLifecycle"
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW
            EXECUTE FUNCTION enforce_review_lifecycle_ownership()
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE CONSTRAINT TRIGGER "ct_Dataset_review_lifecycle_owner"
            AFTER INSERT OR UPDATE OR DELETE ON "Dataset"
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW
            EXECUTE FUNCTION enforce_review_lifecycle_ownership()
            """
        )
    )

    connection.execute(
        sa.text(
            """
            CREATE FUNCTION prevent_review_transition_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF TG_OP = 'UPDATE' THEN
                    RAISE EXCEPTION 'Review transitions are immutable'
                        USING ERRCODE = '55000';
                END IF;

                IF EXISTS (
                    SELECT 1
                    FROM "ReviewLifecycle"
                    WHERE review_lifecycle_id = OLD.review_lifecycle_id
                ) THEN
                    RAISE EXCEPTION 'Review transitions cannot be deleted directly'
                        USING ERRCODE = '55000';
                END IF;

                RETURN OLD;
            END;
            $$
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TRIGGER "tr_ReviewTransition_immutable"
            BEFORE UPDATE OR DELETE ON "ReviewTransition"
            FOR EACH ROW
            EXECUTE FUNCTION prevent_review_transition_mutation()
            """
        )
    )


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Catalogue consolidation requires PostgreSQL/PostGIS")

    connection.execute(
        sa.text(
            'LOCK TABLE "Dataset", "DatasetStaging", "Agent", '
            '"AgentStaging", "Keyword", "KeywordStaging", '
            '"LicenseDocument", "LicenseDocumentStaging", "Location", '
            '"LocationStaging", "Distribution", "datasetKeyword", '
            '"datasetKeywordStaging", "datasetDataTheme", "CatalogStaging", '
            '"DataThemeStaging", "DistributionStaging", '
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

    _create_review_tables()
    op.add_column(
        "Dataset",
        sa.Column("review_lifecycle_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "Dataset",
        sa.Column(
            "review_owner_type",
            sa.String(length=32),
            nullable=True,
            server_default="dataset",
        ),
    )

    _attach_canonical_lifecycles(connection, cutover_at)
    migrated_count = _migrate_staging_datasets(connection, cutover_at)

    op.alter_column("Dataset", "review_lifecycle_id", nullable=False)
    op.alter_column("Dataset", "review_owner_type", nullable=False)
    op.create_check_constraint(
        "ck_Dataset_review_owner_type",
        "Dataset",
        "review_owner_type = 'dataset'",
    )
    op.create_unique_constraint(
        "uq_Dataset_review_lifecycle_id",
        "Dataset",
        ["review_lifecycle_id"],
    )
    op.create_foreign_key(
        "fk_Dataset_review_lifecycle",
        "Dataset",
        "ReviewLifecycle",
        ["review_lifecycle_id", "review_owner_type"],
        ["review_lifecycle_id", "owner_type"],
        ondelete="CASCADE",
        deferrable=True,
        initially="DEFERRED",
    )

    _replace_dataset_foreign_key_with_cascade(
        connection,
        "Distribution",
        "distribution_dataset_id",
    )
    _replace_dataset_foreign_key_with_cascade(
        connection,
        "datasetDataTheme",
        "dataset_id",
    )
    _replace_dataset_foreign_key_with_cascade(
        connection,
        "datasetKeyword",
        "dataset_id",
    )

    final_count = connection.execute(
        sa.text('SELECT COUNT(*) FROM "Dataset"')
    ).scalar_one()
    if final_count != original_main_count + migrated_count:
        raise RuntimeError(
            "Catalogue consolidation produced an unexpected Dataset row count"
        )

    lifecycle_count = connection.execute(
        sa.text('SELECT COUNT(*) FROM "ReviewLifecycle"')
    ).scalar_one()
    transition_count = connection.execute(
        sa.text('SELECT COUNT(*) FROM "ReviewTransition"')
    ).scalar_one()
    owned_lifecycle_count = connection.execute(
        sa.text(
            'SELECT COUNT(*) FROM "ReviewLifecycle" lifecycle '
            'JOIN "Dataset" dataset '
            "ON dataset.review_lifecycle_id = lifecycle.review_lifecycle_id "
            "AND dataset.review_owner_type = lifecycle.owner_type"
        )
    ).scalar_one()
    if lifecycle_count != final_count or transition_count != lifecycle_count:
        raise RuntimeError(
            "Catalogue consolidation produced unexpected lifecycle or transition counts"
        )
    if owned_lifecycle_count != lifecycle_count:
        raise RuntimeError(
            "Catalogue consolidation produced an invalid lifecycle owner count"
        )

    _create_review_triggers(connection)


def downgrade() -> None:
    raise RuntimeError(
        "Catalogue consolidation is irreversible; restore the matching database "
        "backup and application release instead."
    )
