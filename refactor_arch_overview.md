# Shared Review Lifecycle Architecture

## Purpose

The application currently stores review lifecycle state directly on `Dataset`. Future record types, including research sites and potentially instruments, will require the same submission and review process.

The intended architecture centralizes this behavior so that:

- Every reviewable record uses the same transition graph.
- Lifecycle fields and validation rules are defined once.
- Every record has exactly one lifecycle.
- A lifecycle cannot be shared between unrelated record types.
- Every state transition is recorded immutably.
- Review comments and reviewer identities are retained historically.
- Dataset-specific metadata, including `modified`, remains on `Dataset`.
- Future record types can join the workflow without duplicating lifecycle logic.

In addition, the temporary local editor bypass remains available for development testing.

## Lifecycle States

All reviewable records use the states:

| Status | Meaning | Public |
| --- | --- | --- |
| `submitted` | Submitted and awaiting review | No |
| `revision` | Changes have been requested | No |
| `rejected` | Review completed without acceptance | No |
| `accepted` | Accepted and publicly available | Yes |

The shared transition graph is then:

```text
submitted -> revision
submitted -> rejected
submitted -> accepted

revision -> submitted
revision -> rejected

rejected -> revision

accepted -> revision
```

Revision and rejection require review feedback.

## Core Models

### ReviewLifecycle

`ReviewLifecycle` stores the current lifecycle snapshot for one reviewable record.

It will have/has fields:

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
- An accepted lifecycle has an acceptance timestamp.
- Revision and rejection have non-empty current review feedback.
- Each lifecycle has exactly one owner.
- The owner type agrees with the type of record referencing it.

### ReviewTransition

`ReviewTransition` stores an immutable lifecycle event.

It will have/has fields:

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

foreseen actor modes are:

```text
authenticated
anonymous
local_bypass
migration
system
```

Authenticated review actions store the reviewer's OIDC subject in `actor_id`.

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

Transition rows cannot be edited or individually deleted. Under the deletion policy (cascading on deletion of lifecycle; see below), deleting the complete owning record also deletes its lifecycle and transition history. This choice is favored over soft-deletion/permanent archiving to more easily allow submitting users to request complete deletion of records.

## Record Ownership

Each reviewable record references one lifecycle through a typed relationship.

A dataset contains:

```text
review_lifecycle_id
review_owner_type = "dataset"
```

E.g., a research site will contain:

```text
review_lifecycle_id
review_owner_type = "research_site"
```

The owner type is constrained in each record table and participates in a composite foreign key to `ReviewLifecycle`.

This prevents invalid cross-type sharing. For example, a lifecycle declared as belonging to a dataset cannot also be assigned to a research site (including through raw SQL).

A deferred database constraint validates at transaction completion that every lifecycle has exactly one owner of the declared type.

Future record types add their own fixed owner type and typed lifecycle relationship without duplicating lifecycle fields.

## Deletion Semantics

`ReviewLifecycle` is the parent of the record and its transition history.

Deletion starts at the lifecycle:

```text
ReviewLifecycle
    -> owning Dataset, ResearchSite, or other record
    -> associated ReviewTransition rows
```

Foreign-key cascades delete the complete aggregate.

Application code must therefore delete the lifecycle rather than deleting the dataset or research site directly. Database ownership constraints prevent direct owner deletion from silently leaving an orphan lifecycle.

The transition history is immutable while the record exists, but is intentionally removed when the complete record is hard-deleted.

## Current State And Historical State

`ReviewLifecycle.current_review_comment` contains the feedback relevant to the current state.

`ReviewTransition.review_comment` permanently records the feedback supplied during each transition.

This duplication is intentional:

- Current-state queries and administration remain simple.
- Acceptance can clear the current review comment.
- Historical comments remain available in transition records.
- Revision and rejection can be validated without querying the transition history.
- The current lifecycle and its transition are updated atomically.

## Record-Specific Modification Time

`modified` remains on each domain record rather than moving into `ReviewLifecycle`.

For a dataset, it continues to represent the most recent metadata or workflow change affecting that dataset.

The generic transition service updates the owner's `modified` timestamp whenever the lifecycle changes.

Future record types must expose their own `modified` field if they participate in this workflow.

## Generic Transition Service

Dataset-specific transition logic is/will be replaced by a shared service:

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

The service (will):

1. Validate the transition against the shared graph.
2. Require feedback for revision and rejection.
3. Create an immutable `ReviewTransition`.
4. Update the current `ReviewLifecycle` snapshot.
5. Update the record-specific `modified` timestamp.
6. Leave transaction commit responsibility with the caller.

All lifecycle state changes must pass through this service during normal application operation.

NOTE:
A (temporary) `transition_dataset()` wrapper may be retained while existing call sites are migrated.

## Submission

A public dataset submission creates the following objects atomically:

```text
ReviewLifecycle(status="submitted")
ReviewTransition(from_status=NULL, to_status="submitted")
Dataset
```

The transition actor is:

- The authenticated OIDC subject when available.
- Anonymous when no authenticated submitter exists.

AI extraction is prefill-only. It creates no dataset, lifecycle, or transition until the user explicitly submits the completed form.

## Administration

Flask-Admin continues to provide the current review interface.

Normal metadata editing does not expose lifecycle relationships or system-managed fields directly.

Lifecycle actions use the generic transition service:

- Accept
- Request revision
- Reject
- Resubmit

Revision and rejection collect review feedback as part of the transition operation. Feedback is not saved independently before the transition.

The reviewer identity is captured from the authenticated session. When the local bypass is active, the transition is explicitly recorded as originating from `local_bypass`.

Admin deletion deletes the lifecycle parent, causing the complete dataset and transition history to be removed.

The local bypass remains disabled by default and continues to affect only Flask-Admin access. It does not grant access to the currently retained direct edit and delete routes. These may be deprecated or altered at a later date.

## Public Visibility

Only records whose lifecycle status is `accepted` are publicly visible.

Dataset queries therefore join `Dataset` to `ReviewLifecycle` when enforcing visibility.

This applies to:

- Dataset detail.
- Download-list display.
- Adding records to the download list.
- Export.
- Catalogue serialization.
- Dashboard counts.
- Elasticsearch rebuilding.
- Database validation of Elasticsearch search results.

Lifecycle counts remain scoped to the requested record type. Dataset dashboard statistics must not include other types (e.g. research-site or instrument lifecycles).

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

The lifecycle relationship must be eagerly loaded during bulk serialization to prevent one additional database query per record.

Elasticsearch continues to contain only accepted datasets.

## Database Events And Synchronization

Lifecycle changes make `ReviewLifecycle` dirty, not necessarily the owning dataset. Database event handling must therefore recognize both record and lifecycle changes.

The synchronization cycle will:

1. Detect metadata changes to a reviewable record.
2. Detect lifecycle changes.
3. Resolve the lifecycle owner.
4. Update the owner's record-specific `modified` timestamp.
5. Queue the typed record identity.
6. Commit PostgreSQL.
7. Reload the committed owner.
8. Index accepted records or remove non-accepted records.
9. Clear pending synchronization work after rollback.

The synchronization queue becomes type-aware so future record types can use separate indexing behavior.

## Migration

The existing previous consolidation migration has not been deployed. It is therefore rewritten directly.

The rewritten migration will:

1. Preserve all current legacy staging validation.
2. Create `ReviewLifecycle`.
3. Create `ReviewTransition`.
4. Add the typed lifecycle relationship to `Dataset`.
5. Create an accepted lifecycle for every existing canonical dataset.
6. Create a lifecycle for every migrated non-approved staging dataset.
7. Create one migration-snapshot transition for every lifecycle.
8. Preserve rejected review feedback.
9. Preserve record-specific `modified` values.
10. Add lifecycle, transition, and ownership constraints.
11. Retain legacy staging tables unchanged.
12. Validate record, lifecycle, transition, and ownership counts.

Historical transition sequences cannot be reconstructed reliably. Migrated records therefore receive one explicit migration-snapshot transition representing their state at cutover. The retained staging tables remain the archive for older review details.

No lifecycle fields will be added directly to `Dataset`.

## Integrity Guarantees

The intended database guarantees are:

- Every reviewable record has one lifecycle.
- Every lifecycle has one owner.
- A lifecycle cannot be shared across record types.
- Owner type and lifecycle owner type agree.
- Current lifecycle state satisfies the status-specific constraints.
- Every transition references an existing lifecycle.
- Transition comments satisfy transition-specific requirements.
- Transition rows are immutable while their owner exists.
- Deleting the lifecycle removes the complete owned aggregate.

## Performance Considerations

The normalized structure introduces:

- One indexed join for lifecycle-based record queries.
- One lifecycle row per record.
- One transition row per lifecycle event.
- Two-row writes for current state and transition history.

Expected overhead is modest at the current registry scale.

The design should avoid:

- Lazy-loading one lifecycle per serialized record.
- Hybrid properties that hide correlated status subqueries.
- Counting all lifecycle rows when record-type-specific counts are required.
- Loading transition history for ordinary public queries.

Indexes should support:

```text
ReviewLifecycle(owner_type, status)
ReviewTransition(review_lifecycle_id, changed_at)
ReviewTransition(actor_id)
```

## Testing Expectations

Coverage will verify:

- Shared transition behavior.
- Strict cross-type ownership.
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
- Record-type-specific dashboard statistics.
