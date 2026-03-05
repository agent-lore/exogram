# Target Search Schema (Registry)

This document is the canonical target schema for search projections.

It exists to prevent drift across plans and to batch schema-breaking rebuilds where possible.

Normative references:

- `unified-write-contract.md`
- `final-architecture-guardrails.md`

## Tantivy Document Fields

Required fields (target end state):

- `id` (stored)
- `title` (text/stored)
- `content` (text/stored)
- `path` (stored)
- `author` (stored)
- `tags` (stored)
- `created_at` (stored)
- `updated_at` (stored)
- `expires_at` (stored, optional)
- `source_url` (stored, raw for exact matching)

Notes:

- URL lookups should use exact term-query helpers, not naive unquoted query strings.
- `expires_at`/`updated_at` are surfaced for freshness; filtering/ranking logic can use them as needed.

## Chroma Chunk Metadata Fields

Required metadata fields (target end state):

- `doc_id`
- `chunk_index`
- `title`
- `path`
- `author`
- `tags`
- `source_url` (optional)
- `updated_at` (optional)
- `expires_at` (optional)

## Rebuild Strategy

When any target field addition/removal requires backend schema changes:

1. detect mismatch at startup
2. recreate affected index
3. run full rebuild in same boot

Batching rule:

- if multiple adjacent features require schema-breaking changes, prefer one combined schema jump and one rebuild window.

