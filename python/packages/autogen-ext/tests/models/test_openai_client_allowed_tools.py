from typing import Any, Dict, List, Set, cast
from unittest.mock import AsyncMock

import pytest
from autogen_core.models import UserMessage
from autogen_core.tools import CodeExecutorTool, FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage


@pytest.mark.asyncio
async def test_tool_choice_without_tools_raises() -> None:
    def add(x: int, y: int) -> int:
        return x + y

    tool = FunctionTool(add, description="add")
    client = OpenAIChatCompletionClient(model="gpt-5", api_key="test-key")

    with pytest.raises(ValueError, match="tool_choice specified but no tools provided"):
        await client.create(messages=[UserMessage(content="hi", source="user")], tool_choice=tool)


@pytest.mark.asyncio
async def test_tool_choice_references_missing_tool_raises() -> None:
    def a(x: int) -> int:
        return x

    def b(y: int) -> int:
        return y

    tool_a = FunctionTool(a, description="a")
    tool_b = FunctionTool(b, description="b")
    client = OpenAIChatCompletionClient(model="gpt-5", api_key="test-key")

    with pytest.raises(ValueError, match=r"tool_choice references\ '"):
        await client.create(messages=[UserMessage(content="hi", source="user")], tools=[tool_a], tool_choice=tool_b)


@pytest.mark.asyncio
async def test_allowed_tools_includes_function_and_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    def add(x: int, y: int) -> int:
        return x + y

    func_tool = FunctionTool(add, description="calculator")
    custom_tool = CodeExecutorTool()

    mock_response = ChatCompletion(
        id="id",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(role="assistant", content="ok"),
            )
        ],
        created=0,
        model="gpt-5",
        object="chat.completion",
        usage=CompletionUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )

    async_mock_client = AsyncMock()
    async_mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    def mock_client_factory(*_a: Any, **_k: Any) -> AsyncMock:
        return async_mock_client

    monkeypatch.setattr("autogen_ext.models.openai._openai_client._openai_client_from_config", mock_client_factory)

    client = OpenAIChatCompletionClient(model="gpt-5", api_key="test-key")

    await client.create(
        messages=[UserMessage(content="hi", source="user")],
        tools=[func_tool, custom_tool],
        allowed_tools=[func_tool.name, custom_tool],
        tool_choice="auto",
    )

    call_kwargs: Dict[str, Any] = async_mock_client.chat.completions.create.call_args.kwargs  # type: ignore[assignment]
    assert "tool_choice" in call_kwargs
    tc = call_kwargs["tool_choice"]
    assert isinstance(tc, dict)
    tc_typed = cast(Dict[str, Any], tc)
    assert tc_typed.get("type") == "allowed_tools"
    assert tc_typed.get("mode") == "auto"
    tools_list = tc_typed.get("tools", [])
    assert isinstance(tools_list, list)
    tools_list_typed = cast(List[Dict[str, Any]], tools_list)
    names: Set[str] = set()
    for tool_dict in tools_list_typed:
        if isinstance(tool_dict, dict) and "name" in tool_dict:
            name = cast(str, tool_dict.get("name"))
            names.add(name)
    assert func_tool.name in names
    assert custom_tool.name in names


@pytest.mark.asyncio
async def test_invalid_tool_choice_string_raises() -> None:
    def add(x: int, y: int) -> int:
        return x + y

    tool = FunctionTool(add, description="add")
    client = OpenAIChatCompletionClient(model="gpt-5", api_key="test-key")

    with pytest.raises(ValueError, match="tool_choice must be a Tool/CustomTool object"):
        await client.create(
            messages=[UserMessage(content="hi", source="user")],
            tools=[tool],
            tool_choice="not-a-valid-mode",  # type: ignore[arg-type]
        )
