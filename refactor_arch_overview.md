# Shared Review Lifecycle Architecture

## Purpose

The application stores current dataset review state in `ReviewLifecycle` and immutable lifecycle events in `ReviewTransition`. `Dataset` retains its record-specific metadata, including `modified`, and references its lifecycle through a typed one-to-one relationship.

The implemented architecture centralizes this behavior so that:

- Every supported reviewable record uses the same transition graph.
- Lifecycle behavior and validation rules are shared rather than repeated for each owner type.
- Every dataset has exactly one lifecycle.
- A lifecycle cannot be shared between datasets or referenced under a mismatched owner type.
- Normal application transitions are recorded as immutable events.
- Review comments and reviewer identities are retained for the lifetime of the aggregate.
- Dataset-specific metadata, including `modified`, remains on `Dataset`.
- Future record types can reuse the workflow without duplicating lifecycle logic.

Datasets are currently the only supported reviewable owner type. Adding another type requires explicit schema constraints, ownership-trigger logic, ORM relationships, and synchronization dispatch. The local editor bypass remains available for development testing and is disabled by default.

## Lifecycle States

The dataset lifecycle uses the states:

| Status | Meaning | Public |
| --- | --- | --- |
| `submitted` | Submitted and awaiting review | No |
| `revision` | Changes have been requested | No |
| `rejected` | Review completed without acceptance | No |
| `accepted` | Accepted and publicly available | Yes |

The shared workflow service enforces this transition graph:

```text
submitted -> revision
submitted -> rejected
submitted -> accepted

revision -> submitted
revision -> rejected

rejected -> revision

accepted -> revision
```

Revision and rejection require review feedback. Database constraints validate state values and feedback requirements, while the transition graph itself is enforced by the application workflow service.

## Core Models

### ReviewLifecycle

`ReviewLifecycle` stores the current lifecycle snapshot for one dataset.

It has these fields:

```text
review_lifecycle_id
owner_type
status
submitted_at
accepted_at
current_review_comment
submitter_id
```

The lifecycle contains current operational state, not the immutable history.

Constraints enforce that:

- `status` is one of the supported values.
- `submitted_at` is always present.
- An accepted lifecycle has an acceptance timestamp.
- Revision and rejection have non-empty current review feedback.
- The currently supported owner type is `dataset`.
- Each lifecycle has exactly one dataset owner and its owner type agrees with the referencing record.

The exact-one-owner rule is installed by the Alembic migration as a deferred PostgreSQL constraint trigger. It is not installed by `metadata.create_all()` alone. An acceptance timestamp is retained if an accepted record later moves to revision.

### ReviewTransition

`ReviewTransition` stores an append-only lifecycle event.

It has these fields:

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

A transition records:

- The state before the transition.
- The resulting state.
- When the transition occurred.
- The review feedback associated with it.
- The identity responsible for the transition, when available.
- The context in which the transition was performed.

Supported actor modes are:

```text
authenticated
anonymous
local_bypass
migration
system
```

Authenticated submission call sites store the submitter's OIDC UserInfo subject, and administration call sites store the reviewer's UserInfo subject, in `actor_id`. The generic workflow validates that authenticated activity has a non-empty identity and that other actor modes do not have one.

Transitions performed through the local editor bypass use:

```text
actor_id = NULL
actor_mode = "local_bypass"
```

This preserves local testing without inventing a fake identity.

Migration-generated transitions use:

```text
actor_id = NULL
actor_mode = "migration"
```

The Alembic migration installs PostgreSQL triggers that prevent transition updates and individual deletion while the parent lifecycle exists. Under the deletion policy, deleting the lifecycle cascades through its transition history and owned dataset aggregate. This is favored over soft deletion or permanent archiving so submitting users can request complete deletion of records.

## Record Ownership

Each dataset references one lifecycle through a typed relationship.

A dataset contains:

```text
review_lifecycle_id
review_owner_type = "dataset"
```

The owner type is fixed to `dataset` and participates in a deferred composite foreign key to `ReviewLifecycle`. The lifecycle reference is unique.

This prevents lifecycle reuse and mismatched typed references, including through raw SQL.

A deferred PostgreSQL constraint validates at transaction completion that every lifecycle has exactly one dataset owner.

Future record types must add their own fixed owner type and typed lifecycle relationship, then extend the supported owner constraint, ownership trigger, ORM relationships, and synchronization dispatcher.

## Deletion Semantics

`ReviewLifecycle` is the parent of the dataset and its transition history.

Deletion starts at the lifecycle:

```text
ReviewLifecycle
    -> owning Dataset
    -> associated ReviewTransition rows
    -> Dataset-owned distributions and association rows
```

Foreign-key cascades delete the complete aggregate.

Application code must therefore delete the lifecycle rather than deleting the dataset directly. Database ownership constraints prevent direct dataset deletion from silently leaving an orphan lifecycle. Referenced records such as agents, catalogues, keywords, data themes, locations, licences, media types, and checksums survive; only the owned dataset, distributions, transitions, and dataset association rows are deleted.

The transition history is immutable while the record exists, but is intentionally removed when the complete record is hard-deleted.

## Current State And Historical State

`ReviewLifecycle.current_review_comment` contains the feedback relevant to the current review cycle. Resubmission preserves the feedback that prompted revision, while acceptance clears it.

`ReviewTransition.review_comment` immutably records the feedback supplied during each transition for the lifetime of the aggregate.

This duplication is intentional:

- Current-state queries and administration remain simple.
- Acceptance can clear the current review comment.
- Historical comments remain available in transition records.
- Revision and rejection can be validated without querying the transition history.
- The workflow service updates the current lifecycle and its transition in one caller-controlled transaction.

## Record-Specific Modification Time

`modified` remains on each domain record rather than moving into `ReviewLifecycle`.

For a dataset, it continues to represent the most recent metadata or workflow change affecting that dataset.

The generic transition service updates the owner's `modified` timestamp whenever the lifecycle changes.

Lifecycle-aware database events also update the owner timestamp when lifecycle data changes outside an explicit workflow timestamp. Future record types must expose their own `modified` field if they participate in this workflow.

## Generic Lifecycle Services

`initialize_reviewable()` creates a submitted lifecycle and initial event without committing:

```python
initialize_reviewable(
    record,
    submitter_id=None,
    actor_id=None,
    actor_mode="anonymous",
    changed_at=None,
)
```

It attaches a `submitted` lifecycle, appends the initial `NULL -> submitted` transition, applies one timestamp to the lifecycle, event, and owner record, and validates the reviewable-record contract.

`transition_reviewable()` implements shared state changes:

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

The service:

1. Validates the transition against the shared graph.
2. Requires feedback for revision and rejection.
3. Creates an immutable `ReviewTransition`.
4. Updates the current `ReviewLifecycle` snapshot.
5. Updates the record-specific `modified` timestamp.
6. Leaves transaction commit responsibility with the caller.

For persisted records, it locks and refreshes the lifecycle with `SELECT ... FOR UPDATE` before validation. Detached persisted records are rejected because they cannot be locked safely. All normal runtime lifecycle changes use these generic services; there is no dataset-specific `transition_dataset()` wrapper.

## Submission

A valid explicit submission through `/stage_dataset` creates the following objects atomically:

```text
ReviewLifecycle(status="submitted")
ReviewTransition(from_status=NULL, to_status="submitted")
Dataset
```

The transition actor is:

- The authenticated OIDC subject when available.
- Anonymous when no authenticated submitter exists.

The transaction records authenticated provenance from verified OIDC UserInfo when available and otherwise records anonymous provenance. Persistence failures roll back the dataset, lifecycle, transition, and related helper rows. AI extraction is prefill-only and creates no database records until the user explicitly submits the completed form.

## Administration

Flask-Admin provides lifecycle-aware columns and filters plus a dedicated CSRF-protected review page. The review page displays the current snapshot and ordered transition history, including timestamps, comments, actor identities, and actor modes.

Normal metadata editing does not expose lifecycle relationships or system-managed fields directly.

The dedicated review page offers every transition allowed from the current state through the generic transition service:

- Accept
- Request revision
- Reject
- Resubmit

Revision and rejection collect review feedback as part of the transition operation. Feedback is not saved independently before the transition. Acceptance and resubmission may include an optional audit note.

Only acceptance and resubmission are available as atomic bulk actions. Revision and rejection are excluded because they require record-specific feedback.

The reviewer identity is captured from the authenticated session. When the local bypass is active, the transition is explicitly recorded as originating from `local_bypass`.

Admin deletion deletes the lifecycle parent, causing the complete dataset and transition history to be removed.

The local bypass remains disabled by default and affects only Flask-Admin access. It does not grant access to the retained direct edit and delete routes, which continue to require their normal editor authorization.

## Public Visibility

Only individual records whose lifecycle status is `accepted` are publicly visible.

Dataset queries therefore join `Dataset` to `ReviewLifecycle` when enforcing visibility.

This applies to:

- Dataset detail.
- Download-list display.
- Adding records to the download list.
- Export.
- Catalogue serialization.
- Elasticsearch rebuilding.
- Database validation of Elasticsearch search results.

The public dashboard is an intentional exception: it reports aggregate dataset counts for all four lifecycle states without exposing non-accepted records. Counts join through `Dataset`, so they remain dataset-scoped if more owner types are added later.

## Serialization And Elasticsearch

The database relationship is normalized, but public and Elasticsearch serialization remains flattened.

A dataset document continues to contain:

```json
{
  "status": "accepted",
  "submitted_at": "...",
  "accepted_at": "..."
}
```

It does not expose:

```text
current_review_comment
submitter_id
actor_id
actor_mode
review transition history
```

The lifecycle relationship uses select-in loading, and accepted-query paths reuse their joined lifecycle row, avoiding one query per serialized record.

Rebuilds and successful incremental synchronization keep only accepted datasets in Elasticsearch. Synchronization is best-effort after the PostgreSQL commit, so a failed operation can temporarily leave a stale document. Public search remains fail-closed by filtering accepted status and revalidating results against PostgreSQL.

## Database Events And Synchronization

Lifecycle changes make `ReviewLifecycle` dirty, not necessarily the owning dataset. Database event handling recognizes both dataset and lifecycle changes.

The implemented synchronization cycle:

1. Detect new, changed, and deleted datasets and new or changed lifecycle rows.
2. Resolve lifecycle ownership and capture deletion identities before database cascades.
3. Update `Dataset.modified` while preserving an explicit workflow timestamp.
4. Queue a deduplicated `(owner_type, owner_id)` identity.
5. Commit PostgreSQL.
6. Process queued identities in deterministic order from a separate session.
7. Reload each owner from committed PostgreSQL state.
8. Index accepted datasets or remove missing and non-accepted documents.
9. Isolate and log failures per identity so later work can continue.

Rollback clears all pending synchronization work without contacting Elasticsearch. The queue is type-aware, but the current dispatcher supports only `dataset`. Future owner types require an explicit handler. Elasticsearch failures do not reverse a successful PostgreSQL commit; recovery uses a full index rebuild.

## Migration

Alembic revision `9f4e2c1d7a30` implements the forward-only consolidation from revision `251acb193b99`. Operators upgrading that revision must follow the [catalogue migration runbook](docs/catalogue-migration.md), including its preflight, backup, maintenance-window, validation, and rollback procedures.

The migration:

1. Locks and validates the canonical and staging source data.
2. Creates `ReviewLifecycle`.
3. Creates `ReviewTransition`.
4. Adds the typed lifecycle relationship to `Dataset`.
5. Creates an accepted lifecycle for every existing canonical dataset.
6. Maps pending and resubmitted staging datasets to `submitted`, and final rejected staging datasets to `rejected`.
7. Creates one migration-snapshot transition for every lifecycle.
8. Preserves rejected and resubmission feedback.
9. Preserves existing canonical `modified` values and assigns each migrated staging record the latest non-null value among its legacy `modified`, `rejected_at`, and `resubmitted_at` timestamps.
10. Adds lifecycle, transition, cascade, and ownership constraints and triggers.
11. Retains legacy staging tables unchanged.
12. Validates record, lifecycle, transition, and ownership counts.

Historical transition sequences cannot be reconstructed reliably. Migrated records therefore receive one explicit migration-snapshot transition representing their state at cutover. The retained staging tables remain an operationally read-only archive for older review details; database privileges or triggers do not enforce read-only access.

No lifecycle state fields are stored directly on `Dataset`; it contains only the typed lifecycle reference fields `review_lifecycle_id` and `review_owner_type`.

## Integrity Guarantees

In an Alembic-upgraded PostgreSQL database, constraints and migration-installed triggers guarantee:

- Every dataset has one lifecycle.
- Every lifecycle has exactly one dataset owner.
- A lifecycle cannot be shared between datasets.
- Owner type and lifecycle owner type agree.
- Current lifecycle state satisfies the status-specific constraints.
- Every transition references an existing lifecycle.
- Transition values, comments, actor provenance, and non-self transitions satisfy their constraints.
- Transition rows cannot be updated or individually deleted while their lifecycle exists.
- Deleting the lifecycle removes the complete owned aggregate.

The application workflow additionally enforces the allowed transition graph, row locking, and creation of one history event per normal state change. The database does not independently prove that every snapshot update has a corresponding event, that an event follows the workflow graph, or that the latest event agrees with the current snapshot. Migration and normal runtime code are the controlled paths that maintain those invariants.

## Performance Considerations

The normalized structure introduces:

- One indexed join for lifecycle-based record queries.
- One lifecycle row per record.
- One transition row per lifecycle event.
- A normal transition inserts a history row, updates the lifecycle snapshot, and updates `Dataset.modified`.

Expected overhead is modest at the current registry scale.

The implementation avoids:

- Lazy-loading one lifecycle per serialized record.
- Hybrid properties that hide correlated status subqueries.
- Counting lifecycle rows without joining through `Dataset`.
- Loading transition history for ordinary public queries.

The implemented indexes support:

```text
ReviewLifecycle(owner_type, status)
ReviewTransition(review_lifecycle_id, changed_at)
ReviewTransition(actor_id)
```

## Implementation And Verification Status

The above has been implemented in 5 major logical blocks (steps 1-5). Further details of each are available in respective markdown documents step-0X-...


Focused and full-suite coverage verifies:

- Shared transition behavior.
- Typed dataset ownership and rejection of unsupported owner types.
- Exactly one lifecycle per record.
- Immutable transitions.
- Reviewer identity and comments.
- Honest local-bypass provenance.
- Atomic submission.
- Cascade hard deletion.
- Record-specific modification timestamps.
- Accepted-only public visibility.
- Correct Elasticsearch synchronization.
- Flattened public serialization.
- Migration preservation and ownership counts.
- Dataset-scoped dashboard statistics.

The shared test factory creates deterministic lifecycle-backed datasets through `initialize_reviewable()` and `transition_reviewable()`. Faker-based bulk generation remains available for tests that require varied data. 

The migration runbook contains the detailed preflight, deployment, reconciliation, index rebuild, smoke-test, and rollback procedure. The README retains only generic migration guidance and a warning for databases at revision `251acb193b99`. The changelog identifies the consolidation as a breaking, forward-only change.

Production rehearsal against a restored backup, restoration verification, live reconciliation, Elasticsearch rebuilding, and smoke testing remain deployment operations rather than implementation work.
