# Step 1: Shared Lifecycle Persistence

## Role In The Overall Design

This step establishes the normalized database foundation for the shared review workflow. It moves current review state out of `Dataset`, introduces immutable transition history, and makes `ReviewLifecycle` the parent of a typed reviewable-record aggregate.

Later steps will use this persistence layer for workflow operations, public visibility, administration, and search synchronization. Those application integrations are intentionally outside this step.

## Intended Structure

### ReviewLifecycle

`ReviewLifecycle` stores the current review state for exactly one reviewable record. It contains:

```text
review_lifecycle_id
owner_type
status
submitted_at
accepted_at
current_review_comment
submitter_id
```

Database constraints validate supported states, accepted timestamps, required revision or rejection feedback, and the currently supported owner types.

An indexed `(owner_type, status)` pair supports type-scoped status queries. A unique `(review_lifecycle_id, owner_type)` pair is the target of typed owner foreign keys.

### ReviewTransition

`ReviewTransition` stores an append-only event for a lifecycle. It contains:

```text
review_transition_id
review_lifecycle_id
from_status
to_status
changed_at
review_comment
actor_id
actor_mode
```

Database constraints validate statuses, required feedback, actor provenance, and non-self transitions. Indexes support ordered lifecycle history and actor-based audit queries.

### Dataset Ownership

`Dataset` replaces its direct lifecycle fields with:

```text
review_lifecycle_id
review_owner_type = "dataset"
```

The pair forms a composite foreign key to `ReviewLifecycle`. The lifecycle reference is unique, and a check constraint fixes the dataset owner type to `dataset`.

Deleting a lifecycle cascades to its dataset. Dataset-owned distributions, keyword links, and data-theme links also receive database cascades so they cannot block aggregate deletion.

## Exact Ownership Enforcement

A deferred PostgreSQL constraint trigger checks the final transaction state for every lifecycle affected through either the lifecycle or dataset table. At commit it requires one dataset owner for every lifecycle whose owner type is `dataset`.

Deferral permits the lifecycle and owner to be inserted in either flush order. It also rejects direct owner deletion, lifecycle reuse, unsupported owner types, and transactions that leave an orphan lifecycle.

The composite foreign key independently prevents an owner from referencing a lifecycle declared for another record type.

## Transition Immutability

A PostgreSQL trigger rejects all direct transition updates.

It also rejects direct transition deletion while the parent lifecycle exists. When the lifecycle itself is deleted, the foreign-key cascade removes its transitions after the parent is no longer visible, allowing deliberate aggregate deletion without permitting individual audit-history deletion.

## Migration Strategy

The undeployed catalogue-consolidation revision is rewritten rather than extended with another migration.

The migration will:

1. Preserve existing source validation and locking.
2. Create the lifecycle and transition tables.
3. Add nullable typed lifecycle references to `Dataset` during backfill.
4. Create accepted lifecycle snapshots for existing canonical datasets.
5. Create lifecycle snapshots for migrated non-approved staging datasets.
6. Create one `migration` transition for every lifecycle.
7. Preserve rejected feedback and record-specific `modified` timestamps.
8. Make dataset lifecycle references non-null after backfill.
9. Add typed ownership and aggregate cascade constraints.
10. Install deferred ownership and transition-immutability triggers.
11. Reconcile dataset, lifecycle, transition, and owner counts.
12. Leave legacy staging tables unchanged as the historical archive.

## Verification Scope

Focused tests will cover:

- Lifecycle status, timestamp, and feedback constraints.
- Transition status, comment, and actor constraints.
- Unique typed dataset ownership.
- Cross-type references and orphan lifecycle rejection.
- Direct transition update and deletion rejection.
- Lifecycle-driven dataset and transition cascade deletion.
- Cascade deletion of dataset-owned dependent rows.
- Migration state mapping and migration snapshot transitions.
- Preservation of staging records, feedback, relationships, and modification times.
- Atomic rollback when migration preflight fails.

Ownership and trigger behavior will be tested against a real Alembic-upgraded PostgreSQL database because `metadata.create_all()` does not install migration-defined functions and triggers.

## Implementation Record

### Shared Models

`application/models.py` now defines common review status, owner, and actor-mode constants. The existing dataset status names remain temporary aliases so deferred application modules continue to import while they are migrated in later steps.

`ReviewLifecycle` contains the current status snapshot and has:

- Status, owner-type, accepted-timestamp, and feedback checks.
- A unique typed identity for composite owner references.
- Type-and-status and submitter indexes.
- One-to-one dataset and ordered transition relationships.
- Database-passive deletion so PostgreSQL controls aggregate cascades.

`ReviewTransition` contains immutable audit-event data and has:

- Source and target status checks.
- Required feedback for revision and rejection.
- Actor-mode and actor-identity consistency checks.
- A non-self-transition check.
- Lifecycle-history and actor indexes.
- A cascading lifecycle foreign key.

`Dataset` now contains only `review_lifecycle_id` and its fixed `review_owner_type` lifecycle fields. Its composite lifecycle foreign key is `DEFERRABLE INITIALLY DEFERRED`, allowing lifecycle and owner rows to be inserted in either order within one transaction.

The lifecycle reference is unique, the owner type is fixed to `dataset`, and lifecycle deletion cascades into the dataset. Dataset foreign keys from distributions, keyword links, and data-theme links now cascade as well.

### Database Enforcement

The rewritten Alembic revision creates a deferred `enforce_review_lifecycle_ownership()` constraint function and installs constraint triggers on both `ReviewLifecycle` and `Dataset`.

At transaction validation, the function examines both old and new lifecycle references and requires each surviving dataset lifecycle to have exactly one matching dataset owner. A lifecycle deletion is allowed because the parent no longer exists when its cascading owner deletion is checked. Direct dataset deletion fails because its lifecycle remains orphaned.

The `prevent_review_transition_mutation()` trigger rejects every update. It rejects deletion while the parent lifecycle exists but permits the foreign-key cascade after lifecycle deletion. Real PostgreSQL tests verify both paths.

### Migration Data Mapping

The existing source validation and staging-copy helpers remain in place. The revised migration now:

- Creates lifecycle and transition tables before data movement.
- Adds temporary nullable typed lifecycle references to `Dataset`.
- Creates accepted lifecycle snapshots for existing canonical datasets.
- Maps pending and resubmitted staging datasets to `submitted`.
- Maps rejected, non-resubmitted staging datasets to `rejected`.
- Preserves rejection feedback and record-specific modification timestamps.
- Creates one transition with `actor_mode = "migration"` per lifecycle.
- Makes dataset lifecycle references mandatory after backfill.
- Replaces all dataset-dependent foreign keys with database cascades.
- Reconciles dataset, lifecycle, transition, and matching-owner counts.
- Installs ownership and immutability triggers after validated backfill.

Legacy staging tables remain unchanged.

### Test Changes

`test/test_dataset_constraints.py` now verifies ORM-declared lifecycle, transition, actor, typed-owner, and unique-owner constraints.

`test/test_dataset_lifecycle_migration.py` now verifies normalized migration output, absence of direct dataset lifecycle fields, migration snapshot transitions, preservation of source data, owner-first insertion, orphan rejection, owner deletion rejection, transition immutability, and lifecycle-driven cascade deletion across datasets, transitions, distributions, keyword links, and data-theme links.


### Verification

Focused command:

```text
docker compose run --rm --no-deps --build app python -m unittest test.test_dataset_constraints test.test_dataset_lifecycle_migration
```

Final result:

```text
Ran 17 tests in 2.561s
OK
```

### Sequential Boundary

This step intentionally removes direct lifecycle columns before adapting workflow, routes, administration, serialization, and search synchronization. focused persistence and migration tests pass, but the complete application suite is not expected to pass until later groups of edits replace those direct-field call sites.
