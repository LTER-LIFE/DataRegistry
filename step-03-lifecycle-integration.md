# Step 3: Lifecycle Integration And Administration

## Role In The Overall Design

This step completes application-facing integration of the shared lifecycle. It moves public visibility, serialization, dashboard statistics, and maintainer review presentation onto `ReviewLifecycle` while preserving the public dataset document shape.

Automatic database-event and Elasticsearch synchronization changes remain for a later step.

## Accepted Dataset Queries

Every public database read that depends on acceptance will explicitly join `Dataset` to `ReviewLifecycle` and filter on `ReviewLifecycle.status = "accepted"`.

This includes dataset detail, download-list operations, export, index rebuild selection, search-result validation, catalogue serialization, and dashboard statistics. Bulk reads will eagerly load lifecycle rows to avoid per-record lifecycle queries.


## Public Serialization

`Dataset.to_dict()` will continue to expose flattened `status`, `submitted_at`, and `accepted_at` fields sourced from the lifecycle relationship.

Current review feedback, submitter identity, reviewer identity, actor mode, and transition history remain private and are excluded from public and Elasticsearch documents.

NOTE:
`Catalog.to_dict()` will include only related datasets whose lifecycle is accepted.

## Dashboard Statistics

Dataset statistics will join the lifecycle table and group by lifecycle status. Joining through `Dataset` keeps counts scoped to datasets when other reviewable owner types are introduced.

The dashboard presentation remains unchanged.

## Flask-Admin Review List

The review list will display lifecycle status, submission time, modification time, current feedback, and a link to a dedicated record review page. Lifecycle filters will use relationship-aware database joins rather than copied dataset fields.

Ordinary metadata editing will continue to exclude lifecycle relationships, typed ownership fields, system timestamps, submitter identity, and transition history.

## Dedicated Review Page

A CSRF-protected per-record page will display the current lifecycle snapshot and ordered transition history, including timestamps, comments, actor identities, and actor modes.

The transition form will offer only states allowed from the current lifecycle state. Revision and rejection require feedback. Acceptance and resubmission may include an optional audit note.

Every submitted action will call `transition_reviewable()`. Validation or persistence failure will roll back and create no history event.

## Bulk Actions

Revision and rejection will be removed from bulk actions because each record requires explicit feedback. Accept and resubmit can remain as atomic bulk actions and will continue to record actor provenance and lock lifecycle rows in deterministic order.

All valid transitions remain available from the dedicated review page.

## Verification Scope

Focused tests will cover:

- Accepted-only detail, download-list, export, and search-result visibility.
- Flattened public lifecycle serialization.
- Exclusion of private lifecycle and transition data.
- Accepted-only catalogue serialization.
- Dataset-scoped dashboard counts.
- Eager lifecycle loading for bulk serialization.
- Lifecycle-aware admin columns and filtering.
- Dedicated review-page history and valid target choices.
- Required feedback and atomic failure behavior.
- Authenticated and local-bypass provenance.
- Removal of revision and rejection bulk actions.
- Protection of lifecycle fields from metadata editing.

## Implementation Record

Application-facing integration of `ReviewLifecycle` for datasets is now complete:

- Public dataset queries now join the lifecycle table and return only accepted records for detail, download-list, export, index rebuild, and search-result validation paths.
- Dataset and catalogue serialization preserve the existing flattened public shape while excluding feedback, identities, actor modes, and transition history.
- Dataset lifecycle relationships use select-in loading, and accepted-query paths use the joined lifecycle row to avoid per-record lifecycle queries.
- Dashboard status counts are grouped through dataset-owned lifecycle rows.
- Flask-Admin now presents lifecycle columns and filters, protects lifecycle fields from metadata editing, and links each row to a dedicated review page.
- The review page displays the current lifecycle and ordered history, validates CSRF, limits target choices to valid transitions, and delegates changes to `transition_reviewable()`.
- Revision and rejection bulk actions were removed. Accept and resubmit remain atomic bulk actions with actor provenance.
- Shared fixtures and route, model, search-index, dashboard, and admin tests now create and inspect lifecycle-backed state.

Automatic database-event and Elasticsearch synchronization remains intentionally deferred to a following step

Verification completed with:

```text
docker compose run --rm --no-deps --build app python -m unittest test.test_dataset_constraints test.test_dataset_lifecycle_migration test.test_workflow test.routes.test_submission test.test_admin_access test.test_dataset test.routes.test_dataset test.routes.test_dashboard test.test_search_index

Ran 67 tests in 3.984s
OK
```

`git diff --check` also completed without errors.
