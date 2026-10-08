# Step 2: Shared Lifecycle Workflow

## Role In The Overall Design

This step connects application write operations to the shared persistence foundation. It creates lifecycle aggregates for new submissions, records every normal state change as an immutable transition, captures actor provenance, and ensures deletion begins at the lifecycle parent.

Other functionality like Public read filtering, dashboard statistics, complete Flask-Admin presentation, and Elasticsearch synchronization is deferred to later steps.

## Intended Structure

### Lifecycle Initialization

A generic initializer creates the lifecycle for a new reviewable record:

```python
initialize_reviewable(
    record,
    submitter_id=None,
    actor_id=None,
    actor_mode="anonymous",
    changed_at=None,
)
```

The initializer attaches a submitted lifecycle, appends the initial `NULL -> submitted` transition, sets the record-specific modification timestamp, and leaves transaction control with the caller.

### Lifecycle Transitions

A generic service replaces dataset-specific state mutation:

```python
transition_reviewable(
    record,
    target_status,
    review_comment=None,
    actor_id=None,
    actor_mode="authenticated",
    changed_at=None,
)
```

The service validates the shared transition graph, requires feedback for revision and rejection, appends an immutable transition, updates the current lifecycle snapshot, and advances the owner record's `modified` timestamp without committing.

Invalid operations must not modify either current state or transition history.

## Actor Provenance

Authenticated activity uses the OIDC subject as `actor_id` with `actor_mode = "authenticated"`. Anonymous submissions use no actor identifier and `actor_mode = "anonymous"`. Flask-Admin operations performed through the development bypass use no fabricated identifier and `actor_mode = "local_bypass"`.

OIDC subject extraction will be centralized in the authentication module so submission and administration apply the same identity rules.

## Submission

After successful form validation, `/stage_dataset` creates the dataset, lifecycle, and initial transition as one transaction. Invalid forms and AI-prefill requests remain non-persistent.

Persistence errors roll back the session before the route returns an error.

## Deletion

Direct and administrative deletion will delete `dataset.review_lifecycle` rather than the dataset row. PostgreSQL then removes the owned aggregate through the cascades established in Step 1.

Shared keyword and data-theme records are not deleted; only their association rows are part of the aggregate cascade.

## Minimal Administration Integration

Flask-Admin will be made persistence-compatible in this step by excluding lifecycle internals from ordinary metadata editing, using the generic transition service for actions, recording authenticated or local-bypass provenance, and deleting through the lifecycle parent.

Complete lifecycle columns, filters, transition-history presentation, and dedicated revision or rejection feedback input remain for a following step.

## Verification Scope

Focused tests will cover:

- Initial lifecycle and transition creation.
- Authenticated and anonymous provenance.
- Shared transition-graph enforcement.
- Immutable transition append behavior.
- Required review feedback.
- Lifecycle snapshot and modification-time updates.
- Honest local-bypass provenance.
- Atomic submission behavior.
- Non-persistent AI prefill.
- Direct and administrative lifecycle-parent deletion.
- Survival of shared keyword and data-theme records.

## Implementation Record

### Generic Workflow

`application/workflow.py` now provides `initialize_reviewable()` and `transition_reviewable()`.

Initialization validates the record contract, normalizes actor identity, creates a submitted lifecycle, appends the initial `NULL -> submitted` transition, attaches the typed owner, and applies one timestamp to the lifecycle, transition, and record-specific `modified` field.

Transitions validate the current state, actor provenance, and review feedback before mutating any object. A successful transition appends an immutable history event and updates the lifecycle snapshot and owner modification time without committing.

Acceptance sets `accepted_at` and clears current feedback. Revision and rejection replace current feedback. Resubmission preserves the feedback that prompted the revision so it remains available during renewed review.

### Concurrent Review Protection

For persisted records, the transition service obtains a `SELECT ... FOR UPDATE` lock on the lifecycle and refreshes its state before validation. This serializes decisions against one lifecycle and prevents two reviewers with stale in-memory state from appending contradictory transitions that would otherwise leave the final snapshot to last-write-wins behavior.

Transient records can still be exercised without a database lock. Persisted detached records are rejected because they cannot be safely serialized or saved.

Flask-Admin sorts selected dataset identifiers before transition processing to keep lock ordering deterministic for multi-record actions.

### Actor Provenance

`application.authentication.oidc_subject()` obtains the subject from the authoritative OIDC UserInfo response. It does not trust an unverified JWT payload and also supports opaque OAuth access tokens.

Submission provenance is recorded as:

- `authenticated` with the UserInfo subject when available.
- `anonymous` with no actor identifier otherwise.

Administration provenance is recorded as:

- `authenticated` with the UserInfo subject for normal SRAM-authorized use.
- `local_bypass` with no fabricated identity while the explicit development bypass is enabled.

### Submission Integration

`/stage_dataset` now creates a `Dataset`, `ReviewLifecycle`, and initial `ReviewTransition` as one aggregate. One timestamp is used for submission and modification, and commit remains the transaction boundary.

Both dataset mutation routes now roll back their scoped session when an exception occurs. A test forces a failure after all aggregate rows have been flushed and verifies that the dataset, lifecycle, transition, and related helper rows are absent after rollback.

AI metadata extraction remains prefill-only and creates no lifecycle or persisted domain records.

### Deletion Integration

The SRAM-protected direct delete route and Flask-Admin deletion now delete `dataset.review_lifecycle`. PostgreSQL cascades through the dataset aggregate.

Tests verify removal of datasets and transition history while shared `Keyword` and `DataTheme` records survive after their association rows are deleted.

### Minimal Administration Integration

Flask-Admin no longer introspects removed direct dataset lifecycle columns. Lifecycle foreign-key internals are excluded from ordinary metadata editing, and the temporary list and filter configuration uses dataset-local fields only.

Transition actions call the generic workflow, resolve actor provenance, roll back all selected changes on failure, and log unexpected errors. Aggregate deletion uses an overridden `delete_model()` implementation.

Dedicated feedback collection and full lifecycle presentation remain intentionally deferred.

### Test Changes

`test/test_workflow.py` verifies initialization, transition rules, comments, timestamps, provenance, duplicate initialization, resubmission feedback, and stale persisted-state refresh under a row lock.

`test/routes/test_submission.py` verifies anonymous and authenticated aggregate creation, initial history, invalid-form atomicity, post-flush rollback, and non-persistent AI prefill.

`test/test_admin_access.py` verifies UserInfo subject resolution, local-bypass and authenticated transition provenance, metadata modification time, administration listing, and aggregate deletion.

`test/routes/test_dataset.py` includes focused coverage of the SRAM-protected direct deletion path and shared-reference preservation.


### Verification

Final focused command:

```text
docker compose run --rm --no-deps --build app python -m unittest test.test_dataset_constraints test.test_dataset_lifecycle_migration test.test_workflow test.routes.test_submission test.test_admin_access test.routes.test_dataset.TestDatasetRoutes.test_direct_delete_removes_lifecycle_but_retains_shared_records
```

Result:

```text
Ran 43 tests in 5.254s
OK
```

`git diff --check` also passes.

### Sequential Boundary

Dataset public-read queries, flattened serialization, dashboard counts, search synchronization, legacy shared fixtures, and complete lifecycle administration remain for following steps. The full application suite is therefore not expected to pass at this intermediate checkpoint.
