"""Integration test for MCP-over-SSE connectivity to a running server."""

import asyncio
import os

import pytest

mcp = pytest.importorskip("mcp", reason="mcp package is only installed in integration CI job")
ClientSession = mcp.ClientSession
sse_client = pytest.importorskip("mcp.client.sse").sse_client

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_mcp_sse_lists_tools():
    """Connect to running Lithos MCP SSE endpoint and verify tool discovery."""
    endpoint = os.environ.get("LITHOS_MCP_URL")
    if not endpoint:
        pytest.skip("Set LITHOS_MCP_URL to run SSE integration test")

    async with sse_client(endpoint) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await asyncio.wait_for(session.initialize(), timeout=20)
            tools = await asyncio.wait_for(session.list_tools(), timeout=20)

    assert len(tools.tools) >= 20
