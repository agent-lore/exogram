# Unified Write Contract

This document is the canonical write contract for Lithos across:

- `lithos_write` (single-item write)
- `lithos_write_batch` (bulk-write v3 item payloads and per-item outcomes)

If another plan conflicts with this document, this document wins.

System-level rollout and compatibility constraints are defined in `final-architecture-guardrails.md`.

## Goals

1. One payload model for single and batch writes.
2. One response envelope for create/update/duplicate outcomes.
3. One manager-layer invariant path (no server-only enforcement).
4. Clear omit-vs-clear behavior on update.

## Canonical Write Fields

Required create fields:

- `title: str`
- `content: str`
- `agent: str`

Required update fields:

- `id: str` (UUID)
- `agent: str`

Optional shared fields (create/update as applicable):

- Core: `tags`, `confidence`, `path`, `source_task`
- Provenance and dedup: `source_url`, `derived_from_ids`
- Freshness: `ttl_hours`, `expires_at`
- LCMA metadata: `note_type`, `namespace`, `access_scope`, `entities`, `status`, `schema_version`
- Concurrency controls (batch and future single-write parity): `if_match_updated_at`, `if_match_hash`
- Idempotency (batch): `idempotency_key`

Mapping rule:

- `source_task` is stored in metadata field `source` (task-oriented provenance).
- `source_url` is stored separately in metadata field `source_url` (URL provenance and dedup key).

## Update Semantics (Omit vs Clear vs Replace)

Update requests must distinguish omitted values from explicit clears.

`source_url`:

- omitted: preserve existing value
- `null`: clear existing value
- `str`: normalize and set (dedup-checked)

`derived_from_ids`:

- omitted: preserve existing value
- `[]`: clear existing value
- non-empty list: replace full set (after normalization/validation)

`ttl_hours` and `expires_at`:

- if both provided: reject (`invalid_input`)
- `ttl_hours`: compute absolute `expires_at` from current UTC time
- `expires_at`: parse and store as UTC instant
- omitted: preserve existing `expires_at` on update
- explicit `expires_at: null`: clear expiry

Other optional fields follow standard patch semantics:

- omitted: preserve
- provided value: replace

## Validation and Invariants

All validation and invariants are manager-owned and shared by single and batch writes.

### Source URL

- Only `http`/`https`.
- Empty/whitespace is invalid.
- Normalize before persistence and dedup checks:
  - lowercase scheme/host
  - remove fragment
  - remove default ports
  - normalize trailing slash
  - sort query params
  - drop tracking params (`utm_*`, `fbclid`)
- Dedup invariant: one normalized `source_url` maps to at most one document ID.

### Derived Provenance

- `derived_from_ids` must be UUIDs.
- Normalize by trim + dedup + sort.
- Reject self-reference on update (`id` in `derived_from_ids`).
- Missing source IDs are non-fatal warnings, not hard errors.

Authority rule:

- Canonical declared lineage is frontmatter `derived_from_ids`.
- Any graph/edges representation is a projection/cache.

### Freshness

- `expires_at` stored in frontmatter as optional datetime.
- Staleness logic uses `expires_at` and optional read-time age cutoffs.

### LCMA Metadata

- Enums must be validated (`note_type`, `access_scope`, `status`).
- Defaults applied when absent.

## Canonical Success Envelope

`lithos_write` and batch per-item outcomes must use:

```python
{"status": "created", "id": "...", "path": "...", "warnings": []}
{"status": "updated", "id": "...", "path": "...", "warnings": []}
{
  "status": "duplicate",
  "duplicate_of": {"id": "...", "title": "...", "source_url": "..."},
  "message": "A document with this source_url already exists.",
  "warnings": []
}
```

Notes:

- `warnings` is always present (possibly empty).
- Typical warning: unresolved `derived_from_ids` references.
- `duplicate` is specific to source URL dedup policy.

## Error Model

Errors are machine-readable and consistent across single and batch write paths.

Core codes:

- `invalid_input`
- `invalid_uuid`
- `duplicate_source_url`
- `path_collision`
- `stale_write_conflict`
- `doc_not_found`
- `internal_error`

Batch-only projection/workflow codes may add:

- `index_backend_unavailable`
- `graph_update_failed`
- `projection_retry_exhausted`

## Single vs Batch Consistency Rules

1. Same validation logic and manager invariants.
2. Same field semantics.
3. Same status envelope for per-item write results.
4. Batch status/reporting adds workflow state only; it does not redefine write semantics.

## Index and Migration Rules

Frontmatter-only additions usually require no content migration.

If search backend schema shape changes (e.g., Tantivy fields), startup must:

1. detect incompatibility
2. recreate index as needed
3. trigger full rebuild in the same boot

## Observability Requirement

Write and batch paths are instrumented through OTEL foundation (`telemetry.py`, `traced`, `lithos_metrics`), not separate telemetry systems.
