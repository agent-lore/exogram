"""CLI contract tests for stable output shape."""

from click.testing import CliRunner
import pytest

from lithos.cli import cli
from lithos.config import LithosConfig, StorageConfig, set_config
from lithos.knowledge import KnowledgeManager

pytestmark = pytest.mark.integration


class TestCLIContracts:
    """Validate current CLI command output contracts."""

    def test_stats_output_shape(self, temp_dir):
        runner = CliRunner()
        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "stats"])

        assert result.exit_code == 0, result.output
        assert "Lithos Statistics" in result.output
        assert "Documents:" in result.output
        assert "Search chunks:" in result.output
        assert "Graph nodes:" in result.output
        assert "Graph edges:" in result.output
        assert "Data directory:" in result.output

    def test_reindex_and_search_output_shape(self, temp_dir):
        config = LithosConfig(storage=StorageConfig(data_dir=temp_dir))
        config.ensure_directories()
        set_config(config)

        knowledge = KnowledgeManager()
        # Use a content term that should appear in full-text snippet output.
        _ = knowledge  # keeps intent explicit for static checkers

        import asyncio

        async def _seed() -> None:
            await knowledge.create(
                title="CLI Contract Seed",
                content="ContractTerm appears here for full-text verification.",
                agent="cli-test",
            )

        asyncio.run(_seed())

        runner = CliRunner()
        reindex = runner.invoke(cli, ["--data-dir", str(temp_dir), "reindex"])
        assert reindex.exit_code == 0, reindex.output
        assert "Found 1 markdown files" in reindex.output
        assert "Indexed 1 documents" in reindex.output
        assert "Total chunks:" in reindex.output

        search = runner.invoke(
            cli,
            ["--data-dir", str(temp_dir), "search", "ContractTerm", "--fulltext", "--limit", "3"],
        )
        assert search.exit_code == 0, search.output
        assert "Full-text search: ContractTerm" in search.output
        assert "1. CLI Contract Seed (score:" in search.output
        assert "Path:" in search.output

    def test_inspect_doc_output_shape(self, temp_dir):
        config = LithosConfig(storage=StorageConfig(data_dir=temp_dir))
        config.ensure_directories()
        set_config(config)
        knowledge = KnowledgeManager()

        import asyncio

        async def _seed():
            return await knowledge.create(
                title="Inspect Contract Doc",
                content="Inspect output shape contract.",
                agent="cli-test",
                tags=["contract", "inspect"],
            )

        doc = asyncio.run(_seed())

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--data-dir", str(temp_dir), "inspect", "doc", doc.id],
        )

        assert result.exit_code == 0, result.output
        assert "Document: Inspect Contract Doc" in result.output
        assert "id:" in result.output
        assert "path:" in result.output
        assert "author:" in result.output
        assert "tags:" in result.output
        assert "size:" in result.output
