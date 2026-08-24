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

`submitted_at` records the original submission, `accepted_at` records the most
recent acceptance, and `modified` records the latest metadata or workflow
change. Revision and rejection require a `review_comment`.

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
later rejection or resubmission event. The preflight output, deployment log,
database backup, and cutover time must be retained as release artifacts so the
fallback is documented for every legacy record.

## Preflight

Run the checks against the database at the previous Alembic revision:

```bash
python -m scripts.catalogue_migration_preflight
```

Use `--database-url` to inspect a database other than the environment-configured
database, and `--json` to capture a machine-readable report. The command starts
a repeatable-read, read-only transaction. It does not modify data.

Exit status `0` means ready, `1` means data blockers were found, and `2` means
the database could not be inspected. The migration repeats the critical checks
while holding write locks; a successful earlier preflight does not replace the
maintenance window.

The migration deliberately blocks on:

- Contradictory approval and rejection state.
- Missing or inconsistent review timestamps and feedback.
- Approved staging records without exactly one canonical scalar match.
- Multiple approved staging records claiming one canonical record.
- Staging catalogues, themes, distributions, checksums, media types, data
  services, or their associations.
- Dataset references to a staging catalogue.

Those structures were not produced by the public dataset form and were not
completely supported by the old transfer implementation. If preflight reports
them, inspect the small set of reported IDs and extend the migration with a
specific tested mapping rather than discarding data or guessing.

## Deployment

1. Run preflight on a restored production backup or acceptance database.
2. Add every discovered data shape to the migration fixture suite.
3. Resolve all blockers and rerun preflight.
4. Stop application writes.
5. Take a full PostgreSQL schema-and-data backup and verify that it restores.
6. Record the Git revision, Alembic revision, preflight JSON, and UTC cutover
   time.
7. Deploy the application and run `alembic upgrade head`.
8. Rebuild Elasticsearch. Only accepted records are indexed and database
   visibility checks prevent stale non-accepted hits from being returned. If an
   incremental Elasticsearch update fails later, the error is logged and an
   administrator must retry with a full rebuild.
9. Compare main and staging counts with the preflight report.
10. Smoke-test submission, review, acceptance, revision, public detail, search,
    download, and export.
11. Keep the legacy staging tables untouched during the verification period.

The old application must not be reopened against the migrated database. It can
approve retained staging rows again and create duplicate canonical records.

## Validation

After upgrade, verify:

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

## Rollback

The consolidation migration is intentionally forward-only. A generated main ID
cannot be mapped safely back into the old graph after new submissions begin.

Before migration commit, PostgreSQL transactional DDL rolls back failures. After
a successful migration, rollback means stopping writes, restoring the matching
full database backup, deploying the matching previous application release, and
rebuilding Elasticsearch. Do not recreate empty staging tables or downgrade only
the application.
