import asyncio
import json
import sys
from abc import ABC, abstractmethod
from typing import TextIO

from autogen_core import (
    Component,
    ComponentBase,
)
from pydantic import BaseModel

from mcp import types as mcp_types

_ELICITATION_CHOICE_SHORTHANDS = {"a": "accept", "d": "decline", "c": "cancel"}


class Elicitor(ABC, ComponentBase[BaseModel]):
    """Abstract base class for handling MCP elicitation requests.

    Elicitors are responsible for processing elicitation requests from MCP servers,
    which typically involve prompting for user input, and sometimes require more structured responses.
    """

    component_type = "mcp_elicitor"

    @abstractmethod
    async def elicit(self, params: mcp_types.ElicitRequestParams) -> mcp_types.ElicitResult | mcp_types.ErrorData: ...


class StreamElicitor(Elicitor):
    """Handle MCP elicitation requests by reading/writing to TextIO streams."""

    def __init__(self, read_stream: TextIO, write_stream: TextIO, timeout: float | None = None) -> None:
        self._read_stream = read_stream
        self._write_stream = write_stream
        self._timeout = timeout

    def _write(self, text: str):
        self._write_stream.writelines(text)
        self._write_stream.flush()

    async def _read(self) -> str:
        """
        Await a single line from `read` without blocking the event loop.

        Returns the raw line including its trailing newline (if any).
        """

        # Read one line from the provided TextIO in a worker thread
        coroutine = asyncio.to_thread(self._read_stream.readline)
        if self._timeout:
            coroutine = asyncio.wait_for(coroutine, self._timeout)
        return await coroutine

    async def elicit(self, params: mcp_types.ElicitRequestParams) -> mcp_types.ElicitResult:
        header = "=== BEGIN MCP ELICITATION REQUEST ==="
        border = "=" * len(header)
        header = f"{border}\n{header}\n{border}"
        prompt = "\n".join(
            [
                header,
                params.message,
                "Choices:",
                "\t[a]ccept",
                "\t[d]ecline",
                "\t[c]ancel",
                "Please enter one of the above options: ",
            ]
        )

        self._write(prompt)

        try:
            action = await self._read()
            action = action.strip().lower()
            action = _ELICITATION_CHOICE_SHORTHANDS.get(action, action)

            result = mcp_types.ElicitResult.model_validate({"action": action})

            if action == "accept" and params.requestedSchema:
                prompt = "\n".join(
                    [
                        "Input Schema:",
                        json.dumps(params.requestedSchema, indent=2),
                        "Please enter a JSON string following the above schema: ",
                    ]
                )

                self._write(prompt)

                content = await self._read()

                result.content = json.loads(content)

            return result
        finally:
            footer = "=== END MCP ELICITATION REQUEST ==="
            border = "=" * len(footer)
            footer = f"{border}\n{footer}\n{border}"
            self._write(footer)


class StdioElicitorConfig(BaseModel):
    timeout: float | None


class StdioElicitor(StreamElicitor, Component[StdioElicitorConfig]):
    """Handle MCP elicitation requests by reading/writing to stdio"""

    component_config_schema = StdioElicitorConfig
    component_provider_override = "autogen_ext.tools.mcp.StdioElicitor"

    def __init__(self, timeout: float | None = None) -> None:
        super().__init__(sys.stdin, sys.stdout, timeout)

    def _to_config(self) -> BaseModel:
        return StdioElicitorConfig(timeout=self._timeout)

    @classmethod
    def _from_config(cls, config: StdioElicitorConfig):
        return StdioElicitor(timeout=config.timeout)
