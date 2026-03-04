# Digest Auto-Linking

## Motivation

When an agent writes a digest or summary note, it should be able to declare which individual notes it synthesises. Lithos should create graph edges automatically rather than requiring the agent to embed `[[wiki-links]]` manually.

The `lithos_write` tool description already references a `derived_from` parameter ("IDs of source knowledge items") but the actual function signature in `server.py` doesn't accept it. This feature completes that design intent.

## Design

### 1. `lithos_write` parameter

Add `derived_from: list[str] | None = None` to the `lithos_write` signature. Each entry is a UUID referencing an existing knowledge document.

### 2. Frontmatter persistence

Add `derived_from: list[str]` to `DocumentMetadata` (default `[]`), persisted in YAML frontmatter. This is consistent with the existing `source` and `supersedes` fields, and makes the provenance chain visible in Obsidian without injecting wiki-links into the content body.

Round-trip: `KnowledgeManager.create`/`update` must accept and store the field; `DocumentMetadata.from_dict` must parse it back.

### 3. Graph edge type attribute

Add an `edge_type` attribute to all graph edges:

- Existing wiki-link edges: `edge_type="wiki_link"`
- New derived-from edges: `edge_type="derived_from"`

In `KnowledgeGraph.add_document`, after processing wiki-links, iterate `doc.metadata.derived_from` and create edges using **direct ID lookup** (not `_resolve_link`, which resolves slugs/aliases). This is a separate code path from wiki-link resolution.

### 4. Validation of derived_from IDs

If a UUID in `derived_from` does not resolve to a node in the graph:

- **Do not fail the write.** The source document may have been deleted or not yet indexed.
- **Do not create `__unresolved__` placeholder nodes.** The existing placeholder mechanism is slug-based and would not work for UUID references.
- Include a `warnings` list in the `lithos_write` response noting any unresolved IDs, e.g. `{"id": "...", "path": "...", "warnings": ["derived_from ID abc123 not found in graph"]}`.

### 5. Update semantics

When `lithos_write` is called with `id` (update mode) and a `derived_from` list, the full set of derived-from edges is **replaced**, not merged. This is consistent with how wiki-link edges already work — `add_document` removes the node and re-adds it, rebuilding all edges from scratch.

If `derived_from` is `None` on update, preserve the existing value from frontmatter (do not clear it).

### 6. `lithos_links` changes

- Include `edge_type` in response objects: `{"id": "...", "title": "...", "edge_type": "wiki_link"}`.
- Add optional `edge_type: str | None = None` filter parameter. When set, only return edges of that type. This enables queries like "show me all digests that synthesise this note" by filtering incoming edges to `edge_type="derived_from"`.

### 7. Backward compatibility for `edge_type`

Existing edges (from cache or rebuilt on reindex) won't have `edge_type`. Treat missing `edge_type` as `"wiki_link"` — this is safe since all pre-existing edges are wiki-link edges.

## Files

| File | Changes |
|------|---------|
| `server.py` | Add `derived_from` param to `lithos_write`; pass to knowledge layer; add warnings to response; update `lithos_links` response and filter param |
| `knowledge.py` | Add `derived_from` to `DocumentMetadata` and `KnowledgeDocument`; handle in `create`/`update`/`from_dict`/`to_markdown` |
| `graph.py` | Add `edge_type` to all `add_edge` calls; add derived-from edge creation path in `add_document`; update `get_links`/`get_broken_links` to respect edge types |

## Scope

Small-medium. The graph infrastructure exists; this adds a new edge type, a new field on the data model, and wires it through the write path. The main complexity is ensuring edge types are threaded through consistently (graph serialization, link queries, broken-link detection).
