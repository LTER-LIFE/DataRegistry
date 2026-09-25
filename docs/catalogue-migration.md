# Single Catalogue Migration

This release changes the application from separate main and staging model
graphs to one canonical `Dataset` table. Physical staging tables are retained
as a read-only migration archive in this release. A later contract migration
can remove them after acceptance and production verification.

## Lifecycle

Canonical records have one of four states:

| Status | Meaning | Public |
| --- | --- | --- |
| `submitted` | Awaiting maintainer review | No |
| `revision` | Changes have been requested | No |
| `rejected` | Review ended negatively | No |
| `accepted` | Published in the registry | Yes |

`ReviewLifecycle` stores the current status, submission and acceptance times,
current review feedback, and submitter identity. `ReviewTransition` stores the
immutable event history and actor provenance. `Dataset.modified` records the
latest metadata or workflow change for the dataset itself. Revision and
rejection require review feedback.

Public and Elasticsearch documents remain flattened and expose `status`,
`submitted_at`, and `accepted_at`. They do not expose review feedback,
identities, actor modes, or transition history.

Anonymous submission remains supported. `submitter_id` contains the OIDC
subject only when the submitting user was authenticated. Maintainers remain
responsible for follow-up on anonymous submissions using contact information in
the metadata record.

AI extraction only populates the normal dataset form. It never creates database
records. The user must review the form and explicitly submit it through the
normal submission endpoint.

## Timestamp Policy

The previous schema did not record a reliable dataset submission timestamp and
did not link an approved staging record to its canonical copy. Existing main
records therefore receive one shared UTC cutover timestamp for both
`submitted_at` and `accepted_at`. Existing `modified` values are preserved.

Migrated pending and rejected records receive the cutover timestamp as
`submitted_at`. Their `modified` timestamp is preserved or advanced to a known
later rejection or resubmission event. The actual cutover timestamp is assigned
by PostgreSQL and stored in the migrated lifecycle rows. Retain the preflight
output, deployment log, database backup, and maintenance-window start time as
release artifacts so the fallback is documented for every legacy record.

## Preflight

The preflight intentionally supports only the previous Alembic revision. Confirm
the current revision before running it:

```bash
docker compose run --rm --no-deps app alembic current
# expected: 251acb193b99

docker compose run --rm --no-deps app \
  python -m scripts.catalogue_migration_preflight --json \
  > catalogue-preflight.json
```

Use `--database-url` to inspect a database other than the environment-configured
database, and `--json` to capture a machine-readable report. The command starts
a repeatable-read, read-only transaction. It does not modify data.

The shell redirection above writes `catalogue-preflight.json` on the host. Retain
that report with the release artifacts. Do not rerun this preflight after the
upgrade; it reports any revision other than `251acb193b99` as a blocker.

Exit status `0` means ready, `1` means data blockers were found, and `2` means
the database could not be inspected. The migration repeats the critical checks
while holding write locks; a successful earlier preflight does not replace the
maintenance window.

The migration deliberately blocks on:

- Contradictory approval and rejection state.
- An approved record without `approved_at`, or a non-approved record with
  `approved_at`.
- A final rejected record without non-empty rejection feedback.
- Approved staging records without exactly one canonical scalar match.
- Multiple approved staging records claiming one canonical record.
- Staging catalogues, themes, distributions, checksums, media types, data
  services, or their associations.
- Dataset references to a staging catalogue.
- Non-approved staging datasets that reuse a canonical `public_id`.
- Invalid geometry referenced by a non-approved staging dataset.

Those structures were not produced by the public dataset form and were not
completely supported by the old transfer implementation. If preflight reports
them, inspect the small set of reported IDs and extend the migration with a
specific tested mapping rather than discarding data or guessing.

Unreferenced staging agents, keywords, locations, and licences are reported as
warnings rather than blockers. They remain available in the retained legacy
tables but are not copied without a dataset reference.

## Deployment

1. Restore a current production backup into acceptance and verify that the
   restore is usable.
2. Check out the release and build its application image without starting the
   web service: `docker compose build app`.
3. Confirm revision `251acb193b99`, run the JSON preflight against acceptance,
   and add every discovered data shape to the migration fixture suite.
4. Resolve all blockers and rerun the acceptance preflight until `ready` is
   `true`.
5. Stop production application writes and keep them stopped through database
   validation. For a single-instance Compose deployment, use
   `docker compose stop app`.
6. Take a full PostgreSQL schema-and-data backup and verify that it restores.
7. Run and retain a final preflight against the now-frozen production database,
   then capture the remaining release artifacts. One-off containers do not
   publish the application port:

   ```bash
   git rev-parse HEAD > catalogue-git-revision.txt
   date -u +"%Y-%m-%dT%H:%M:%SZ" > catalogue-maintenance-start-utc.txt
   docker compose run --rm --no-deps app \
     alembic current > catalogue-alembic-before.txt
   docker compose run --rm --no-deps app \
     python -m scripts.catalogue_migration_preflight --json \
     > catalogue-preflight-production.json
   ```

8. Upgrade the database from a one-off release container and confirm the
   installed revision:

   ```bash
   docker compose run --rm --no-deps app alembic upgrade head
   docker compose run --rm --no-deps app \
     alembic current > catalogue-alembic-after.txt
   # expected: 9f4e2c1d7a30 (head)
   ```

9. While the application remains stopped, compare canonical, lifecycle,
   transition, and retained staging counts with the frozen production preflight
   report and the validation rules below. Verify that migrated lifecycle rows
   contain the shared database-assigned cutover timestamp.
10. Start the application service: `docker compose up --detach app`.
11. Rebuild Elasticsearch through `/rebuild`. Only accepted records are indexed,
   and database visibility checks prevent stale non-accepted hits from being
   returned. If an incremental Elasticsearch update fails later, the error is
   logged and an administrator must retry with a full rebuild.
12. Confirm database and Elasticsearch counts on `/dashboard` after the rebuild.
13. Smoke-test anonymous and authenticated submission, review history,
    acceptance, revision feedback, public detail, search, download, and export.
14. Keep the legacy staging tables untouched during the verification period.

The old application must not be reopened against the migrated database. It can
approve retained staging rows again and create duplicate canonical records.

## Validation

After upgrade, verify:

- Alembic reports `9f4e2c1d7a30 (head)`.
- Every canonical dataset has exactly one typed `ReviewLifecycle` and at least
  one migration or application `ReviewTransition`.
- Existing main datasets are `accepted`.
- Each non-approved staging dataset produced exactly one canonical submitted or
  rejected record.
- Every approved staging record still corresponds to exactly one accepted main
  record.
- All staging table counts and values are unchanged.
- Pending, revision, and rejected IDs return 404 from public detail routes.
- Download and export omit non-accepted records.
- Elasticsearch contains one document per accepted `dataset_id` and no other
  statuses.

Retain the verified backup, acceptance and frozen-production preflight JSON, Git
revision, before-and-after Alembic revisions, maintenance-window start time,
deployment log, count reconciliation (including the database-assigned cutover
timestamp), and smoke-test results together as the migration record.

## Rollback

The consolidation migration is intentionally forward-only. A generated main ID
cannot be mapped safely back into the old graph after new submissions begin.

Before migration commit, PostgreSQL transactional DDL rolls back failures. After
a successful migration, rollback means stopping writes, restoring the matching
full database backup, deploying the matching previous application release, and
rebuilding Elasticsearch. Do not recreate empty staging tables or downgrade only
the application.
