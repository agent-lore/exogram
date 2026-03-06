# Event Delivery Surface (SSE + Webhooks)

Contract note: system-level rollout and compatibility constraints are governed by `final-architecture-guardrails.md`. Write-path semantics referenced here are governed by `unified-write-contract.md`.

## Goal

Add two delivery mechanisms for the internal event bus (`event-bus-plan.md`): SSE for agents with persistent connections, and webhooks for agents that cannot hold open streams. Add MCP tools for webhook management.

The deeper purpose is emergent coordination: agents declare what they care about, and Lithos connects the dots — no polling, no explicit orchestration.

## Dependency

`event-bus-plan.md` (Phase 2) must be complete. `EventBus` and `LithosEvent` must exist and emit on all write/task/delete success paths before delivery mechanisms are wired up.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   LithosServer                      │
│                                                     │
│  MCP Tools ──► EventBus ──► SSE clients (push)      │
│  File Watcher ──►   │    └─► Webhook dispatcher     │
│                     │           └─► HTTP POST        │
│                     └─► In-memory event log          │
└─────────────────────────────────────────────────────┘
```

One `EventBus` instance (from `event-bus-plan.md`), two delivery mechanisms, all events flow through the same path.

## Design

### 1. SSE Endpoint

Mount an additional route on the FastMCP Starlette app:

```python
self.mcp.custom_route("/events", self._sse_endpoint, methods=["GET"])
```

The endpoint:

```
GET /events
  ?types=note.created,task.completed   (optional filter)
  ?tags=research,pricing               (optional filter)
  ?since=<event-id>                    (replay from event ID)
```

Returns `text/event-stream`. Each event:

```
id: <event-uuid>
event: note.created
data: {"agent": "az", "title": "Acme Pricing", "id": "...", "tags": ["pricing"]}
```

SSE clients subscribe to the `EventBus` with their filter and receive events via their `asyncio.Queue`. Replay-from-ID uses the ring buffer from `event-bus-plan.md`.

### 2. Webhook Delivery

#### Storage

Add tables to the existing `coordination.db` (no new database file):

```sql
CREATE TABLE webhooks (
    id          TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    secret      TEXT NOT NULL,
    event_types TEXT,          -- JSON array, NULL = all
    tags        TEXT,          -- JSON array, NULL = all
    created_by  TEXT,
    created_at  TEXT,
    active      INTEGER DEFAULT 1
);

CREATE TABLE webhook_deliveries (
    id          TEXT PRIMARY KEY,
    webhook_id  TEXT,
    event_id    TEXT,
    status      TEXT,          -- 'delivered', 'failed', 'retrying'
    attempts    INTEGER,
    last_attempt TEXT,
    response_code INTEGER
);
```

Add `CoordinationService` methods: `register_webhook`, `list_webhooks`, `delete_webhook`, `log_delivery`.

#### Dispatcher

- `EventBus` fans out events to a webhook delivery queue
- Background `_webhook_worker()` drains the queue
- For each event, load matching webhooks (filtered by `event_types` and `tags`)
- POST with `X-Lithos-Signature: sha256=<hmac>` header
- 3 retries, exponential backoff (1s, 4s, 16s)
- Log delivery attempts to `webhook_deliveries` table
- SQLite-backed queue ensures retries survive server restart

### 3. Extend `EventsConfig`

Add delivery-specific config fields to `EventsConfig` in `config.py`:

```python
class EventsConfig(BaseModel):
    """Event bus and delivery configuration."""

    enabled: bool = True
    event_buffer_size: int = 500

    # Delivery surface (added by event-delivery-plan)
    sse_enabled: bool = True
    webhooks_enabled: bool = True
    max_sse_clients: int = 50
    webhook_timeout_seconds: int = 10
    webhook_max_retries: int = 3
```

### 4. New MCP Tools

```python
lithos_webhook_register(url, secret, event_types, tags, agent)
  → {webhook_id}

lithos_webhook_list(agent)
  → {webhooks: [{id, url, event_types, tags, active}]}

lithos_webhook_delete(webhook_id, agent)
  → {success}

lithos_webhook_deliveries(webhook_id, limit)
  → {deliveries: [{event_id, status, attempts, last_attempt}]}
```

## Usage Patterns

### Agent Zero: polling to event-driven

**Before:** Agent Zero scheduler polls `lithos_list(since=last_check)` every 5 minutes.

**After:** Agent Zero connects to `GET /events?types=note.created,finding.posted` and reacts immediately.

### OpenClaw webhook

```python
lithos_webhook_register(
    url="http://openclaw:18789/hooks/agent",
    secret="shared-secret",
    event_types=["note.created", "task.completed"],
    tags=["ready-to-distribute"],
    agent="openclaw"
)
```

OpenClaw gets a POST the moment Agent Zero writes a note tagged `ready-to-distribute`. No polling.

### Obsidian user edits

The file watcher already emits `note.updated` via the event bus (from `event-bus-plan.md`). With the delivery surface wired in, editing a note in Obsidian fires `note.updated` to all SSE clients and webhooks automatically.

## Open Questions to Decide Before Building

| Question | Options |
| -------- | ------- |
| SSE auth | Open (local infra) vs bearer token (same as MCP) |
| FastMCP route mounting | `custom_route()` API vs separate Starlette/FastAPI app on second port |
| Webhook delivery | Fire-and-forget background task vs persistent queue (SQLite-backed) |
| Event persistence | Ring buffer only (lost on restart) vs append to SQLite |

For a local-first tool: open SSE, `custom_route()` mounting, SQLite-backed delivery queue (so retries survive restarts), ring buffer for SSE replay.

## Files

| File | Change |
| ---- | ------ |
| `src/lithos/events.py` | Extend: add webhook dispatcher, SSE subscriber helpers |
| `src/lithos/coordination.py` | Add `webhooks` + `webhook_deliveries` tables and methods |
| `src/lithos/server.py` | Add `/events` SSE route, add 4 webhook MCP tools |
| `src/lithos/config.py` | Extend `EventsConfig` with delivery fields |
| `tests/test_event_delivery.py` | New: SSE integration, webhook delivery, retry, HMAC signing tests |
