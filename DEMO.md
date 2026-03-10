# Phase 6.5 — SSE Event Delivery Surface

*2026-03-10T17:42:55Z by Showboat 0.6.1*
<!-- showboat-id: 90ed2724-c57e-40fd-b54a-67a2e114d40a -->

## What was built

Phase 6.5 adds an SSE (Server-Sent Events) delivery surface to Lithos, wiring the existing EventBus to a streaming HTTP endpoint.

### Changes

| File | Change |
|---|---|
| `src/lithos/config.py` | Added `sse_enabled: bool = True` and `max_sse_clients: int = 50` to `EventsConfig` |
| `src/lithos/events.py` | Added `get_buffered_since()` and `active_subscriber_count` to `EventBus` |
| `src/lithos/server.py` | Added `_sse_endpoint()` method and `_format_sse()` helper; registered `GET /events` route |
| `tests/test_event_delivery.py` | 25 new tests covering all required scenarios |

```bash
cd /Users/hanuman/.openclaw/workspace/agents/lithos-dev/lithos && PYTHONPATH=src .venv/bin/python -m pytest tests/test_event_delivery.py -v --tb=short 2>&1 | tail -35
```

```output
platform darwin -- Python 3.12.12, pytest-9.0.2, pluggy-1.6.0 -- /Users/hanuman/.openclaw/workspace/agents/lithos-dev/lithos/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/hanuman/.openclaw/workspace/agents/lithos-dev/lithos
configfile: pyproject.toml
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 25 items

tests/test_event_delivery.py::TestFormatSSE::test_basic_format PASSED    [  4%]
tests/test_event_delivery.py::TestFormatSSE::test_tags_in_payload PASSED [  8%]
tests/test_event_delivery.py::TestFormatSSE::test_payload_fields_included PASSED [ 12%]
tests/test_event_delivery.py::TestGetBufferedSince::test_returns_events_after_id PASSED [ 16%]
tests/test_event_delivery.py::TestGetBufferedSince::test_unknown_id_returns_empty PASSED [ 20%]
tests/test_event_delivery.py::TestGetBufferedSince::test_last_event_returns_empty PASSED [ 24%]
tests/test_event_delivery.py::TestSSEReceivesEvents::test_client_receives_emitted_event PASSED [ 28%]
tests/test_event_delivery.py::TestSSEReceivesEvents::test_client_receives_multiple_events PASSED [ 32%]
tests/test_event_delivery.py::TestTypeFilter::test_type_filter_accepts_matching PASSED [ 36%]
tests/test_event_delivery.py::TestTypeFilter::test_type_filter_multiple_types PASSED [ 40%]
tests/test_event_delivery.py::TestTagFilter::test_tag_filter_accepts_matching PASSED [ 44%]
tests/test_event_delivery.py::TestTagFilter::test_untagged_event_rejected_when_tag_filter_set PASSED [ 48%]
tests/test_event_delivery.py::TestReplay::test_since_replays_buffered_events PASSED [ 52%]
tests/test_event_delivery.py::TestReplay::test_since_unknown_id_yields_no_replay PASSED [ 56%]
tests/test_event_delivery.py::TestReplay::test_last_event_id_header_replay PASSED [ 60%]
tests/test_event_delivery.py::TestReplay::test_last_event_id_takes_precedence_over_since PASSED [ 64%]
tests/test_event_delivery.py::TestReplay::test_replay_applies_type_filter PASSED [ 68%]
tests/test_event_delivery.py::TestReplay::test_replay_applies_tag_filter PASSED [ 72%]
tests/test_event_delivery.py::TestMaxClients::test_max_clients_limit_returns_429 PASSED [ 76%]
tests/test_event_delivery.py::TestMaxClients::test_below_limit_returns_streaming_response PASSED [ 80%]
tests/test_event_delivery.py::TestSSEDisabled::test_sse_disabled_returns_503 PASSED [ 84%]
tests/test_event_delivery.py::TestSSEDisabled::test_sse_enabled_returns_stream PASSED [ 88%]
tests/test_event_delivery.py::TestSSEClientCount::test_client_count_increments_decrements PASSED [ 92%]
tests/test_event_delivery.py::TestSSEConfig::test_events_config_sse_defaults PASSED [ 96%]
tests/test_event_delivery.py::TestSSEConfig::test_events_config_sse_override PASSED [100%]

============================= 25 passed in 27.33s ==============================
```
