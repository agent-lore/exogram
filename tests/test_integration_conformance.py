"""Integration conformance tests focused on MCP boundary contracts."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from lithos.config import LithosConfig
from lithos.server import LithosServer, _FileChangeHandler

pytestmark = pytest.mark.integration


async def _call_tool(server: LithosServer, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call an MCP tool and return its JSON payload."""
    result = await server.mcp._call_tool_mcp(name, arguments)

    if isinstance(result, tuple):
        payload = result[1]
        if isinstance(payload, dict):
            return payload

    if hasattr(result, "content"):  # MCP CallToolResult
        content = getattr(result, "content", [])
    else:
        content = result

    if isinstance(content, list) and content:
        text = getattr(content[0], "text", None)
        if isinstance(text, str):
            return json.loads(text)

    raise AssertionError(f"Unable to decode MCP result for tool {name!r}: {result!r}")


async def _wait_for_full_text_hit(server: LithosServer, query: str, doc_id: str) -> None:
    """Wait briefly for projection consistency in search index."""
    for _ in range(20):
        payload = await _call_tool(server, "lithos_search", {"query": query, "limit": 10})
        if any(item["id"] == doc_id for item in payload["results"]):
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"Document {doc_id} not found in search results for query={query!r}")


class TestMCPToolContracts:
    """Contract tests for MCP tool responses."""

    @pytest.mark.asyncio
    async def test_write_read_list_delete_contract(self, server: LithosServer):
        write_payload = await _call_tool(
            server,
            "lithos_write",
            {
                "title": "Conformance Doc",
                "content": "This validates MCP response shape.",
                "agent": "conformance-agent",
                "tags": ["conformance", "contract"],
                "path": "conformance",
            },
        )
        assert set(write_payload) == {"id", "path"}
        assert isinstance(write_payload["id"], str)
        assert write_payload["path"].endswith(".md")
        assert write_payload["path"].startswith("conformance/")

        doc_id = write_payload["id"]
        read_payload = await _call_tool(server, "lithos_read", {"id": doc_id})
        assert read_payload["id"] == doc_id
        assert read_payload["title"] == "Conformance Doc"
        assert isinstance(read_payload["metadata"], dict)
        assert isinstance(read_payload["links"], list)
        assert read_payload["truncated"] is False

        list_payload = await _call_tool(server, "lithos_list", {"path_prefix": "conformance"})
        assert "items" in list_payload
        assert "total" in list_payload
        assert isinstance(list_payload["items"], list)
        assert isinstance(list_payload["total"], int)
        assert any(item["id"] == doc_id for item in list_payload["items"])

        delete_payload = await _call_tool(server, "lithos_delete", {"id": doc_id})
        assert delete_payload == {"success": True}

    @pytest.mark.asyncio
    async def test_projection_consistency_after_write(self, server: LithosServer):
        write_payload = await _call_tool(
            server,
            "lithos_write",
            {
                "title": "Projection Conformance",
                "content": "Index this content for projection consistency checks.",
                "agent": "conformance-agent",
                "tags": ["projection"],
            },
        )
        doc_id = write_payload["id"]

        # Read/list should be immediately consistent with successful write.
        read_payload = await _call_tool(server, "lithos_read", {"id": doc_id})
        assert read_payload["id"] == doc_id

        list_payload = await _call_tool(server, "lithos_list", {"limit": 100})
        assert any(item["id"] == doc_id for item in list_payload["items"])

        # Search is a projection and can converge shortly after write.
        await _wait_for_full_text_hit(server, "projection consistency checks", doc_id)


class TestRestartPersistence:
    """Persistence tests across server restarts."""

    @pytest.mark.asyncio
    async def test_doc_and_task_survive_restart(self, test_config: LithosConfig):
        first = LithosServer(test_config)
        await first.initialize()

        write_payload = await _call_tool(
            first,
            "lithos_write",
            {
                "title": "Restart Durable Doc",
                "content": "This document should survive restart.",
                "agent": "restart-agent",
                "tags": ["durable"],
            },
        )
        doc_id = write_payload["id"]

        task_payload = await _call_tool(
            first,
            "lithos_task_create",
            {
                "title": "Restart Durable Task",
                "agent": "restart-agent",
                "description": "Ensure coordination persistence.",
            },
        )
        task_id = task_payload["task_id"]
        await _call_tool(
            first,
            "lithos_task_claim",
            {
                "task_id": task_id,
                "aspect": "verification",
                "agent": "restart-agent",
                "ttl_minutes": 30,
            },
        )
        first.stop_file_watcher()

        second = LithosServer(test_config)
        await second.initialize()

        read_payload = await _call_tool(second, "lithos_read", {"id": doc_id})
        assert read_payload["title"] == "Restart Durable Doc"

        await _wait_for_full_text_hit(second, "survive restart", doc_id)

        status_payload = await _call_tool(second, "lithos_task_status", {"task_id": task_id})
        assert len(status_payload["tasks"]) == 1
        assert status_payload["tasks"][0]["id"] == task_id
        assert any(c["aspect"] == "verification" for c in status_payload["tasks"][0]["claims"])
        second.stop_file_watcher()


class TestFileWatcherRace:
    """Race-focused file update/delete consistency checks."""

    @pytest.mark.asyncio
    async def test_rapid_update_then_delete_keeps_indices_consistent(self, server: LithosServer):
        doc = await server.knowledge.create(
            title="Watcher Race Doc",
            content="initial",
            agent="race-agent",
            path="watched",
        )
        server.search.index_document(doc)
        server.graph.add_document(doc)

        file_path = server.config.storage.knowledge_path / doc.path
        handler = _FileChangeHandler(server, asyncio.get_running_loop())

        for i in range(10):
            await server.knowledge.update(id=doc.id, agent="race-agent", content=f"v{i}")
            handler._schedule_update(file_path, deleted=False)

        # Simulate noisy file-system ordering near deletion.
        file_path.unlink()
        handler._schedule_update(file_path, deleted=False)
        handler._schedule_update(file_path, deleted=True)
        handler._schedule_update(file_path, deleted=True)

        for _ in range(30):
            search_payload = await _call_tool(server, "lithos_search", {"query": "Watcher Race Doc"})
            in_search = any(item["id"] == doc.id for item in search_payload["results"])
            in_graph = server.graph.has_node(doc.id)
            try:
                await server.knowledge.read(id=doc.id)
                in_knowledge = True
            except FileNotFoundError:
                in_knowledge = False

            if not in_knowledge and not in_search and not in_graph:
                return
            await asyncio.sleep(0.05)

        raise AssertionError(
            "Final state inconsistent after rapid update/delete "
            f"(knowledge={in_knowledge}, search={in_search}, graph={in_graph})"
        )


class TestConcurrencyContention:
    """Contention tests for concurrent MCP operations."""

    @pytest.mark.asyncio
    async def test_parallel_updates_same_document_remain_consistent(self, server: LithosServer):
        created = await _call_tool(
            server,
            "lithos_write",
            {
                "title": "Concurrent Update Doc",
                "content": "initial content",
                "agent": "concurrency-agent",
                "tags": ["concurrency"],
            },
        )
        doc_id = created["id"]

        updates = [
            _call_tool(
                server,
                "lithos_write",
                {
                    "id": doc_id,
                    "title": "Concurrent Update Doc",
                    "content": f"content version {i}",
                    "agent": "concurrency-agent",
                    "tags": ["concurrency", f"v{i}"],
                },
            )
            for i in range(12)
        ]
        results = await asyncio.gather(*updates, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        assert not errors, f"Unexpected tool errors under contention: {errors!r}"

        # Final document should remain readable and structurally valid.
        read_payload = await _call_tool(server, "lithos_read", {"id": doc_id})
        assert read_payload["id"] == doc_id
        assert read_payload["title"] == "Concurrent Update Doc"
        assert read_payload["content"].startswith("content version ")

        # Exactly one document should exist at this path/logical target.
        listing = await _call_tool(server, "lithos_list", {"path_prefix": ""})
        same_title = [item for item in listing["items"] if item["title"] == "Concurrent Update Doc"]
        assert len(same_title) == 1
        assert same_title[0]["id"] == doc_id

    @pytest.mark.asyncio
    async def test_parallel_claims_single_winner(self, server: LithosServer):
        task = await _call_tool(
            server,
            "lithos_task_create",
            {
                "title": "Concurrency Claim Task",
                "agent": "planner",
                "description": "Only one claim should win for same aspect.",
            },
        )
        task_id = task["task_id"]

        claim_attempts = [
            _call_tool(
                server,
                "lithos_task_claim",
                {
                    "task_id": task_id,
                    "aspect": "implementation",
                    "agent": f"worker-{i}",
                    "ttl_minutes": 15,
                },
            )
            for i in range(8)
        ]
        claim_results = await asyncio.gather(*claim_attempts)
        success_count = sum(1 for result in claim_results if result["success"])
        assert success_count == 1

        status = await _call_tool(server, "lithos_task_status", {"task_id": task_id})
        claims = status["tasks"][0]["claims"]
        assert len(claims) == 1
        assert claims[0]["aspect"] == "implementation"


def test_conformance_module_exists():
    """Sanity check to keep this module discoverable in test listings."""
    assert Path(__file__).name == "test_integration_conformance.py"
