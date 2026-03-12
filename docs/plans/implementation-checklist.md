# Implementation Checklist

Normative references:

- `unified-write-contract.md`
- `final-architecture-guardrails.md`

---

## ✅ Completed Phases

- **Phase 0** — Canonical Contracts and Guardrails
- **Phase 1** — Observability Foundation (OTEL)
- **Phase 2a** — Source URL Dedup + Provenance Surface
- **Phase 2b** — Internal Event Bus
- **Phase 3** — Digest Provenance v2 (`derived_from_ids`)
- **Phase 4** — Research Cache and Freshness
- **Phase 6** — Reconcile/Repair Tooling (internal + CLI/admin only; no MCP tool)
- **Phase 6.5** — SSE Event Delivery

---

## ⏸️ Deferred

**Phase 5 — Bulk Write v3**
Deferred until usage data demonstrates a need for batch writes. Single-write throughput is sufficient for current workloads. Plan: `bulk-write-v3.md`.

**Webhooks / Guaranteed Delivery**
No phase assignment. Revisit if a concrete consumer appears. Plans: `event-webhooks-plan.md`, `event-guaranteed-delivery-plan.md`.

---

## 🔵 Active

### Phase 7 — LCMA Rollout

See **`lcma-checklist.md`** for full MVP 1/2/3 breakdown.

Dependencies: Phases 0 through 6.5 complete ✅

---

## 🔲 Pending

### Phase 8 — API Ergonomics Cleanup

- [ ] Replace the flat `lithos_write` option surface with grouped request objects (`provenance`, `freshness`, `lcma`) at the MCP boundary
- [ ] Preserve the canonical on-disk semantics and outcome envelope from `unified-write-contract.md`
- [ ] Add compatibility notes in `docs/SPECIFICATION.md` for the cleaned-up pre-1.0 interface
- [ ] Extend single-write and batch conformance coverage to grouped input objects

Dependencies: Phase 7 MVP 1 complete

Exit criteria:
- Single and batch write APIs are materially easier to use without changing manager-layer semantics
- Grouped request objects have conformance tests proving parity with canonical field semantics

---

### Phase 9 — CLI Extension (Deferred Integration)

- [ ] Revisit `cli-extension-plan.md` after the write and retrieval surfaces stabilize
- [ ] Prioritize CLI phases 1-3 first (JSON output, read/list, CRUD), then graph/coordination/polish

Dependencies: Phases 0 through 8 complete

Exit criteria:
- CLI surfaces are built on top of the stabilized core contracts

---

## 🔄 Cross-Phase Conformance (Continuous)

- [ ] Maintain one conformance suite across single write, batch write, dedup, provenance, freshness, migration/rebuild, reconcile, event emission/delivery, and OTEL instrumentation
- [ ] Block milestone completion if conformance suite regresses
