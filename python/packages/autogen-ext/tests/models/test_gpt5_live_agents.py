from __future__ import annotations

import os
from typing import Final, Optional

import pytest

from autogen_core.models import CreateResult, UserMessage
from autogen_agentchat.messages import TextMessage
from autogen_core.tools import BaseCustomTool, CustomToolFormat
from autogen_ext.models.openai import OpenAIChatCompletionClient, OpenAIResponsesAPIClient
from autogen_agentchat.agents import AssistantAgent


_REQUIRE_KEY: Final[bool] = bool(os.getenv("OPENAI_API_KEY"))
pytestmark = pytest.mark.skipif(not _REQUIRE_KEY, reason="OPENAI_API_KEY not set; skipping live GPT-5 agent tests")


class CodeExecTool(BaseCustomTool[str]):
    def __init__(self) -> None:
        super().__init__(return_type=str, name="code_exec", description="Execute code from freeform text input")

    async def run(self, input_text: str, cancellation_token) -> str:  # type: ignore[override]
        return f"echo:{input_text.strip()}"


def _sql_grammar() -> CustomToolFormat:
    # Ensure required keys are present with exact names per API
    return {
        "type": "grammar",
        "syntax": "lark",
        "definition": (
            "start: select\n"
            "select: \"SELECT\" NAME \"FROM\" NAME \";\"\n"
            "%import common.CNAME -> NAME\n"
            "%import common.WS\n"
            "%ignore WS\n"
        ),
    }


class SQLTool(BaseCustomTool[str]):
    def __init__(self) -> None:
        super().__init__(return_type=str, name="sql_query", description="Run limited SQL", format=_sql_grammar())

    async def run(self, input_text: str, cancellation_token) -> str:  # type: ignore[override]
        return f"sql:{input_text.strip()}"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-5", "gpt-5-mini", "gpt-5-nano"])
async def test_gpt5_reasoning_and_verbosity(model: str) -> None:
    client = OpenAIChatCompletionClient(model=model)
    try:
        result: CreateResult = await client.create(
            messages=[UserMessage(content="Summarize Autogen in one sentence.", source="user")],
            reasoning_effort="high",
            verbosity="high",
            extra_create_args={"max_completion_tokens": 64},
        )
        assert result.finish_reason in {"stop", "length"}
        assert result.usage.prompt_tokens > 0
        assert result.usage.completion_tokens > 0
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-5", "gpt-5-mini", "gpt-5-nano"])
async def test_gpt5_custom_tool_freeform(model: str) -> None:
    client = OpenAIChatCompletionClient(model=model)
    tool = CodeExecTool()
    try:
        result: CreateResult = await client.create(
            messages=[UserMessage(content="Use code_exec to print HELLO", source="user")],
            tools=[tool],
            tool_choice="auto",
            extra_create_args={"max_completion_tokens": 64},
            reasoning_effort="medium",
            verbosity="low",
        )
        assert result.finish_reason in {"stop", "length"}
        assert result.usage.completion_tokens > 0
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-5", "gpt-5-mini", "gpt-5-nano"])
async def test_gpt5_custom_tool_with_grammar_and_allowed_tools(model: str) -> None:
    # Use Responses API for allowed_tools support
    client = OpenAIResponsesAPIClient(model=model)
    sql_tool = SQLTool()
    code_tool = CodeExecTool()
    try:
        result: CreateResult = await client.create(
            input="Issue a query: SELECT users FROM accounts;",
            tools=[sql_tool, code_tool],
            allowed_tools=[sql_tool],
            tool_choice="auto",
            reasoning_effort="low",
            verbosity="medium",
        )
        assert result.finish_reason in {"stop", "length", "tool_calls", "function_calls"}
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-5", "gpt-5-mini", "gpt-5-nano"])
async def test_gpt5_assistant_agent_flow(model: str) -> None:
    model_client = OpenAIChatCompletionClient(model=model)
    try:
        agent = AssistantAgent(
            name="assistant",
            model_client=model_client,
            system_message="Be brief.",
        )
        # Send one turn
        from autogen_core import CancellationToken
        result = await agent.on_messages([TextMessage(content="Say OK.", source="user")], CancellationToken())
        assert result is not None
        # on_messages returns a Response; verify the chat_message is from assistant
        assert getattr(result.chat_message, "source", "") == "assistant"
    finally:
        await model_client.close() 