# Step 4: Lifecycle Search Synchronization

## Role In The Overall Design

This step adapts automatic Elasticsearch synchronization to the shared review lifecycle. Database events must recognize changes to both a reviewable record and its `ReviewLifecycle`, then synchronize only after the PostgreSQL transaction commits.

The synchronization mechanism will remain best-effort after commit. A PostgreSQL commit will not be reversed when Elasticsearch is unavailable; synchronization failures will be logged so an administrator can retry with a full index rebuild.

Public visibility, serialization, lifecycle administration, persistence constraints, and workflow validation were completed in earlier steps.

## Synchronization Invariants

The implementation will preserve these invariants:

- Elasticsearch is never contacted before the database transaction commits.
- Only accepted datasets are present in the Elasticsearch index.
- Submitted, revision, rejected, and deleted datasets are absent from the index.
- Metadata and lifecycle changes synchronize the same owning record at most once per transaction.
- A rollback produces no Elasticsearch write and leaves no queued synchronization work.
- Elasticsearch receives the committed database state, not an in-memory pre-commit snapshot.
- Public documents retain the flattened lifecycle fields and exclude private review data.

## Type-Aware Synchronization Queue

The session queue will store typed record identities rather than dataset IDs alone. Each queue entry will have the form:

```text
(owner_type, owner_id)
```

The dataset identity is therefore:

```text
("dataset", dataset_id)
```

A set will deduplicate repeated metadata and lifecycle changes within one transaction. The owner type makes dispatch explicit and allows future reviewable record types to add their own loading and indexing behavior without overloading dataset logic.

The queue remains session-local and is removed after commit or rollback.

## Database Event Detection

The flush event handling will recognize:

- New, changed, and deleted dataset records.
- Changed dataset metadata and relationships.
- New and changed dataset lifecycle rows.
- Deletion of a lifecycle that owns a dataset.

When a lifecycle changes, the event handler will resolve its owner according to `ReviewLifecycle.owner_type`. Dataset lifecycle changes will resolve through the typed dataset relationship.

Lifecycle deletion requires capturing the typed dataset identity before PostgreSQL applies the ownership cascade. After commit, the missing owner will cause its Elasticsearch document to be removed.


## Modified Timestamp

Dataset metadata edits will continue to update `Dataset.modified` automatically when the caller did not set it explicitly.

A lifecycle change will also update the owning dataset's `modified` timestamp. If `transition_reviewable()` already assigned the transition timestamp to `modified`, the database event will preserve that explicit value rather than replacing it with a later timestamp during flush.

Lifecycle deletion will not attempt to update the owner timestamp because the complete aggregate is being removed.

## Post-Commit Dispatch

After a successful commit, synchronization will:

1. Remove the queued typed identities from the committed session.
2. Open a separate session bound to the same database engine.
3. Process queued identities in deterministic order.
4. Dispatch each identity according to its owner type.
5. Reload the owner and lifecycle from committed PostgreSQL state.
6. Serialize and index an accepted dataset.
7. Delete the Elasticsearch document when the dataset is missing or not accepted.
8. Log an exception for a failed identity and continue processing the remaining queue.
9. Close the synchronization session.

The initial dispatcher will support `dataset`. Future owner types will require an explicit handler rather than silently using dataset behavior.

## Elasticsearch Helpers

Dataset indexing will continue to pass the flattened result of `Dataset.to_dict()` to `index_document_data()`. This preserves the current document shape and temporal coverage transformation.

Any remaining helper that checks a dataset's acceptance state directly will read `dataset.review_lifecycle.status`.

Document deletion will remain idempotent by ignoring Elasticsearch `404` responses.

## Rollback And Failure Behavior

The rollback event will discard the complete typed synchronization queue. A transaction that flushes changes and then rolls back must not update or remove an Elasticsearch document.

Elasticsearch operations occur after PostgreSQL commit and therefore cannot participate in the database transaction. If indexing or deletion fails:

- The committed database state remains authoritative.
- The failure is logged with the typed record identity.
- Other queued identities continue to synchronize.
- Public search remains fail-closed because search results are revalidated against accepted database records.
- Recovery uses the existing full index rebuild operation.


## Expected Files

The implementation is expected to modify:

- `application/database.py` for lifecycle-aware event detection, typed queueing, owner timestamp updates, post-commit dispatch, and rollback cleanup.
- `application/search_index.py` to remove remaining direct dataset lifecycle-field access.
- `test/test_search_sync.py` for lifecycle-backed live synchronization coverage.
- `test/test_search_index.py` only if focused helper coverage requires adaptation.

No schema migration is required for this step.

## Verification Scope

Focused tests will verify:

- Creating and committing a submitted dataset does not create an Elasticsearch document.
- Transitioning a submitted dataset to accepted indexes its committed public document.
- Editing accepted dataset metadata refreshes its indexed document and modification timestamp.
- Transitioning an accepted dataset to revision removes its document.
- A lifecycle-only change queues the owner, updates the owner modification timestamp, and synchronizes the committed owner.
- Deleting an accepted lifecycle aggregate removes the dataset document after the database cascade.
- A flushed transaction that rolls back leaves Elasticsearch unchanged and clears pending work.
- Repeated owner and lifecycle changes in one transaction are deduplicated.
- One failed synchronization operation does not prevent remaining queued identities from being processed.
- Existing search-index, workflow, administration, and lifecycle integration tests continue to pass.


## Implementation Record

Lifecycle-aware search synchronization is now implemented:

- Session-local work is stored as deduplicated `(owner_type, owner_id)` identities.
- Flush handling recognizes dataset and lifecycle changes, resolves typed lifecycle ownership, and captures lifecycle deletion before the database cascade.
- Metadata changes update `Dataset.modified`, while lifecycle changes preserve a timestamp explicitly assigned by `transition_reviewable()` or assign one when the owner was otherwise unchanged.
- Commit handling processes identities in deterministic order through an explicit dataset dispatcher and reloads each owner from committed PostgreSQL state.
- Accepted datasets are serialized and indexed; missing or non-accepted datasets are removed idempotently.
- Synchronization failures are isolated per identity and logged without reversing the database commit or stopping later identities.
- Rollback handling removes all pending typed identities.
- Remaining Elasticsearch helper logic now reads acceptance from `dataset.review_lifecycle.status`.
- Live synchronization fixtures and tests now use `initialize_reviewable()` and `transition_reviewable()`.


Verification completed with:

```text
docker compose run --rm --no-deps --build app python -m unittest test.test_dataset_constraints test.test_dataset_lifecycle_migration test.test_workflow test.routes.test_submission test.test_admin_access test.test_dataset test.routes.test_dataset test.routes.test_dashboard test.test_search_index test.test_search_sync

Ran 72 tests in 5.202s
OK
```

The five live synchronization tests cover accepted indexing, metadata refresh, lifecycle-only synchronization, aggregate deletion, rollback cleanup, queue deduplication, and continuation after an Elasticsearch failure.

`git diff --check` also completed without errors.
