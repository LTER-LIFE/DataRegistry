# Step 5: Final Validation And Deployment Readiness

## Role In The Overall Design

This step closes the shared lifecycle refactor. It removes temporary compatibility names, verifies the complete application and migration behavior, and makes the deployment procedure precise enough to execute and retain as a release record.


## Completion Criteria

The refactor is ready for deployment when:

- Runtime application code contains no direct dataset lifecycle fields or temporary dataset status aliases.
- Intentional legacy staging fields remain available to the migration and preflight tooling.
- The standalone preflight and the migration reject the same supported blocker categories.
- The complete test suite passes through normal `unittest` discovery.
- The migration runbook documents exact commands, expected revisions, retained artifacts, validation, and rollback.
- The repository's MkDocs configuration points to the existing documentation directory and includes the migration runbook.
- Docker Compose configuration and the final Git diff pass structural checks.

## Final Compatibility Cleanup

The temporary aliases below will be removed from `application/models.py`:

```text
DATASET_STATUS_SUBMITTED
DATASET_STATUS_REVISION
DATASET_STATUS_REJECTED
DATASET_STATUS_ACCEPTED
DATASET_STATUSES
```

All runtime integrations now use shared `REVIEW_STATUS_*` names. Repository searches will confirm that application, template, and test code does not read lifecycle state through removed `Dataset` fields.

The audit will not remove intentional occurrences in:

- Legacy staging migrations and retained staging tables.
- The consolidation migration and its preflight tool.
- Flattened public and Elasticsearch document keys.
- Lifecycle and transition model fields.
- Historical implementation records and changelog entries.

## Preflight And Migration Parity

The existing migration policy will remain unchanged. Regression coverage will exercise the blocker categories already implemented by both the standalone preflight and the locked migration validation:

- A staging dataset marked both approved and rejected.
- An approved record without `approved_at`, or a non-approved record with `approved_at`.
- A final rejected record without non-empty review feedback.
- A staging dataset linked to a staging catalogue.
- A non-approved staging dataset that reuses a canonical `public_id`.
- Invalid geometry referenced by a non-approved staging dataset.
- An approved staging dataset without exactly one canonical scalar match.
- Multiple approved staging rows claiming one canonical dataset.
- Rows in staging structures unsupported by the consolidation.

Preflight-only operational behavior will also be covered:

- Unreferenced helper rows produce warnings rather than blockers.
- A ready database returns CLI exit status `0`.
- Data blockers return CLI exit status `1`.
- Configuration or inspection failure returns CLI exit status `2`.
- With --json, preflight emits a machine-readable snapshot of source revisions, counts, warnings, blockers, and reconciliation results that can be retained with the deployment records.

Tests will run against the previous Alembic revision `251acb193b99`. Where a blocker is shared, coverage will verify both the preflight report and atomic migration refusal.

## Deployment Documentation

`docs/catalogue-migration.md` will be updated to state that current lifecycle values are stored in `ReviewLifecycle` and immutable history in `ReviewTransition`, while public documents remain flattened.

The preflight section will list the actual blocker policy rather than using broader timestamp wording. It will provide commands to:

1. Confirm the database is at revision `251acb193b99`.
2. Capture the preflight JSON report outside the container.
3. Record the Git revision and UTC maintenance-window start time.
4. Upgrade to expected head `9f4e2c1d7a30`.
5. Confirm the installed Alembic revision and database-assigned cutover timestamp.
6. Reconcile database counts before starting the application.
7. Rebuild the accepted-only Elasticsearch index.
8. Reconcile index counts and perform submission, review, visibility, search, download, and export smoke tests.

The runbook will continue to require a verified full PostgreSQL backup and a maintenance window. It will emphasize that preflight must run before upgrade and intentionally rejects databases already migrated beyond the expected previous revision.

`README.md` will retain concise setup instructions and direct operators to the runbook for the complete migration procedure and artifact requirements.

## Documentation Build

`docs/mkdocs.yml` currently references documentation pages that do not exist. The existing navigation will be preserved, `docs_dir` will point to the directory containing the configuration, and the catalogue migration runbook will be added to the navigation.

Completing the missing home, installation, and API reference pages has been recorded in `possible_issues.md`. Until those pages are added, the configuration will be validated with a non-strict build whose output is written outside the repository:

```text
docker compose run --rm --no-deps --build app mkdocs build --config-file docs/mkdocs.yml --site-dir /tmp/dataregistry-docs
```

## Full Verification

The primary regression command will use discovery rather than an explicit module list:

```text
docker compose run --rm --no-deps --build app python -m unittest
```

Additional final checks will include:

```text
docker compose config
git diff --check
```

Repository searches will verify removal of temporary aliases and improper direct dataset lifecycle access. Existing deprecation warnings will be reported separately from test failures.

## Expected Files

This step is expected to modify:

- `application/models.py`
- `test/test_dataset_lifecycle_migration.py`
- `docs/catalogue-migration.md`
- `docs/mkdocs.yml`
- `README.md`
- `possible_issues.md`
- `step-05-final-validation.md`

The following files will change only if parity testing exposes a defect:

- `scripts/catalogue_migration_preflight.py`
- `alembic/versions/9f4e2c1d7a30_consolidate_dataset_catalogue.py`



## Implementation Record

Final cleanup and deployment-readiness validation are complete:

- Removed the unused `DATASET_STATUS_*` and `DATASET_STATUSES` compatibility aliases.
- Confirmed that runtime Python code contains no direct dataset lifecycle-field access and no `transition_dataset()` references.
- Expanded migration tests to exercise both approval-timestamp inconsistencies, lifecycle contradictions, missing final rejection feedback, staging catalogue references, public-ID conflicts, invalid geometry, duplicate approved claims, and every unsupported staging structure.
- Added coverage that orphaned supported helper rows remain warnings and that preflight CLI exits are `0` for ready, `1` for blocked, and `2` for inspection failure.
- Confirmed that the standalone preflight and locked migration validation agree across the supported blocker policy.
- Updated the migration runbook with normalized lifecycle storage, exact blocker semantics, one-off migration containers, acceptance and frozen-production preflight artifacts, expected revisions, accepted-only index rebuilding, reconciliation, smoke tests, and rollback evidence.
- Updated the README setup and release procedures to use the runbook and avoid starting the web service before migration.
- Preserved the complete MkDocs navigation, set `docs_dir: .`, and added the migration runbook. The eight missing documentation pages are recorded in `possible_issues.md`.

The documentation-build plan set to non-strict so the future but currently missing MkDocs pages could remain in navigation. The build succeeds and reports those eight known warnings.

Verification completed with:

```text
docker compose run --rm --no-deps --build app python -m unittest test.test_dataset_lifecycle_migration

Ran 7 tests in 3.983s
OK
```

```text
docker compose run --rm --no-deps --build app python -m unittest

Ran 74 tests in 5.446s
OK
```

```text
docker compose run --rm --no-deps --build app mkdocs build --config-file docs/mkdocs.yml --site-dir /tmp/dataregistry-docs

Documentation built successfully with eight expected missing-page warnings.
```

`docker compose config --quiet` and `git diff --check` completed without errors. Repository audits returned no matches for temporary dataset status aliases, direct dataset lifecycle fields, or `transition_dataset()`.

Deployment rehearsal against a restored production backup, backup restoration verification, live count reconciliation, Elasticsearch rebuilding, and smoke testing remain to-be-performed steps documented in `docs/catalogue-migration.md`.
