"""
Bilig WorkPaper MCP example.

This example connects AutoGen's McpWorkbench to a local Bilig WorkPaper MCP
server over stdio. The server exposes a formula workbook as tools, so an
agent or workflow can read cells, write input cells, recalculate formulas,
verify readback, and persist the WorkPaper JSON document without automating
Excel or a browser.

The default smoke test does not require an LLM API key:

    python bilig_workpaper_mcp_example.py

Prerequisites: Python dependencies for `autogen-ext[mcp]` and Node.js/npm for
launching the `bilig-workpaper-mcp` stdio server with `npm exec`.

Optional agent demo:

    export OPENAI_API_KEY="your-api-key"
    uv run --with autogen-agentchat --with 'autogen-ext[openai,mcp]' python bilig_workpaper_mcp_example.py --agent
"""

import argparse
import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from autogen_core import CancellationToken

from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def bilig_server_params(workpaper_path: Path) -> StdioServerParams:
    """Return stdio params for a writable Bilig demo WorkPaper."""
    return StdioServerParams(
        command="npm",
        args=[
            "exec",
            "--yes",
            "--package",
            "@bilig/workpaper@latest",
            "--",
            "bilig-workpaper-mcp",
            "--workpaper",
            str(workpaper_path),
            "--init-demo-workpaper",
            "--writable",
        ],
        read_timeout_seconds=60,
    )


async def call_json(workbench: McpWorkbench, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Call a WorkPaper MCP tool and parse its JSON text response."""
    result = await workbench.call_tool(name, arguments or {}, CancellationToken())
    if result.is_error:
        raise RuntimeError(f"{name} failed: {result}")

    if not result.result:
        raise RuntimeError(f"{name} returned no result content")

    return json.loads(result.result[0].content)


async def run_tool_smoke() -> None:
    """Run a no-key tool smoke test against the WorkPaper MCP server."""
    workpaper_path = Path(tempfile.mkdtemp(prefix="autogen-bilig-")) / "quote.workpaper.json"

    async with McpWorkbench(server_params=bilig_server_params(workpaper_path)) as workbench:
        tools = await workbench.list_tools()
        logger.info("Tools: %s", [tool["name"] if isinstance(tool, dict) else tool.name for tool in tools])

        inputs = await call_json(workbench, "read_range", {"range": "Inputs!A1:B5"})
        summary = await call_json(workbench, "read_range", {"range": "Summary!A1:B5"})
        logger.info("Inputs: %s", inputs["serialized"])
        logger.info("Summary formulas: %s", summary["serialized"])

        before_arr = await call_json(workbench, "read_cell", {"sheetName": "Summary", "address": "B3"})
        edit = await call_json(
            workbench,
            "set_cell_contents",
            {"sheetName": "Inputs", "address": "B3", "value": 0.4},
        )
        after_customers = await call_json(workbench, "read_cell", {"sheetName": "Summary", "address": "B2"})
        after_arr = await call_json(workbench, "read_cell", {"sheetName": "Summary", "address": "B3"})
        exported = await call_json(workbench, "export_workpaper_document", {"includeConfig": True})

        logger.info("ARR before: %s", before_arr["value"]["value"])
        logger.info("Customers after: %s", after_customers["value"]["value"])
        logger.info("ARR after: %s", after_arr["value"]["value"])
        logger.info("Persisted: %s", edit["checks"]["persisted"])
        logger.info("Restored matches after: %s", edit["checks"]["restoredMatchesAfter"])
        logger.info("Exported bytes: %s", exported["serializedBytes"])
        logger.info("WorkPaper path: %s", workpaper_path)

        assert before_arr["value"]["value"] == 60000
        assert after_customers["value"]["value"] == 8
        assert after_arr["value"]["value"] == 96000
        assert edit["checks"]["persisted"] is True
        assert edit["checks"]["restoredMatchesAfter"] is True
        assert workpaper_path.exists()


async def run_agent_demo() -> None:
    """Run an optional AutoGen assistant over the same WorkPaper tools."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY before running the optional --agent demo.")

    try:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.ui import Console

        from autogen_ext.models.openai import OpenAIChatCompletionClient
    except ImportError as exc:
        raise RuntimeError(
            "Install optional agent dependencies before running --agent: "
            "uv run --with autogen-agentchat --with 'autogen-ext[openai,mcp]' "
            "python bilig_workpaper_mcp_example.py --agent"
        ) from exc

    workpaper_path = Path(tempfile.mkdtemp(prefix="autogen-bilig-agent-")) / "quote.workpaper.json"

    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    try:
        async with McpWorkbench(server_params=bilig_server_params(workpaper_path)) as workbench:
            assistant = AssistantAgent(
                "workpaper_assistant",
                model_client=model_client,
                workbench=workbench,
                system_message=(
                    "You are a workbook automation assistant. Use the WorkPaper tools to inspect inputs, "
                    "edit input cells, verify recalculated formula readback, and report persistence status."
                ),
            )

            await Console(
                assistant.run_stream(
                    task=(
                        "Increase the win rate to 40%, then report expected customers, "
                        "expected ARR, and whether the WorkPaper JSON persisted."
                    )
                )
            )
    finally:
        await model_client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoGen Bilig WorkPaper MCP example")
    parser.add_argument("--agent", action="store_true", help="Run the optional OpenAI-backed agent demo")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.agent:
        await run_agent_demo()
    else:
        await run_tool_smoke()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        raise SystemExit(f"Error: {exc}") from None
