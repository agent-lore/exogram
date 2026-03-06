# Lithos Quick Guide

- Goal: local, privacy-first MCP shared memory for AI agents.
- Core: Markdown+YAML knowledge, Tantivy full-text, Chroma semantic, NetworkX wiki-link graph, SQLite coordination.
- Stack: Python 3.10+ (`src/lithos`), pytest, Ruff.

## Done Criteria (Required)

A change is **not done** unless all four are green:

1. Unit tests: `uv run --extra dev pytest -m "not integration" tests/ -q`
2. Integration tests: `uv run --extra dev pytest -m integration tests/ -q`
3. Lint: `uv run --extra dev ruff check .`
4. Format check: `uv run --extra dev ruff format --check src/ tests/`
