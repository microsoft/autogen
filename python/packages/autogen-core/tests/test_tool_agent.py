import asyncio
import json
from typing import Any, AsyncGenerator, List, Mapping, Optional, Sequence, Union

import pytest
from autogen_core import AgentId, CancellationToken, FunctionCall, SingleThreadedAgentRuntime
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelCapabilities,
    RequestUsage,
    UserMessage,
)
from autogen_core.tool_agent import (
    InvalidToolArgumentsException,
    ToolAgent,
    ToolExecutionException,
    ToolNotFoundException,
    tool_agent_caller_loop,
)
from autogen_core.tools import FunctionTool, Tool, ToolSchema


def _pass_function(input: str) -> str:
    return "pass"


def _raise_function(input: str) -> str:
    raise Exception("raise")


async def _async_sleep_function(input: str) -> str:
    await asyncio.sleep(10)
    return "pass"


@pytest.mark.asyncio
async def test_tool_agent() -> None:
    runtime = SingleThreadedAgentRuntime()
    await ToolAgent.register(
        runtime,
        "tool_agent",
        lambda: ToolAgent(
            description="Tool agent",
            tools=[
                FunctionTool(_pass_function, name="pass", description="Pass function"),
                FunctionTool(_raise_function, name="raise", description="Raise function"),
                FunctionTool(_async_sleep_function, name="sleep", description="Sleep function"),
            ],
        ),
    )
    agent = AgentId("tool_agent", "default")
    runtime.start()

    # Test pass function
    result = await runtime.send_message(
        FunctionCall(id="1", arguments=json.dumps({"input": "pass"}), name="pass"), agent
    )
    assert result == FunctionExecutionResult(call_id="1", content="pass")

    # Test raise function
    with pytest.raises(ToolExecutionException):
        await runtime.send_message(FunctionCall(id="2", arguments=json.dumps({"input": "raise"}), name="raise"), agent)

    # Test invalid tool name
    with pytest.raises(ToolNotFoundException):
        await runtime.send_message(FunctionCall(id="3", arguments=json.dumps({"input": "pass"}), name="invalid"), agent)

    # Test invalid arguments
    with pytest.raises(InvalidToolArgumentsException):
        await runtime.send_message(FunctionCall(id="3", arguments="invalid json /xd", name="pass"), agent)

    # Test sleep and cancel.
    token = CancellationToken()
    result_future = runtime.send_message(
        FunctionCall(id="3", arguments=json.dumps({"input": "sleep"}), name="sleep"), agent, cancellation_token=token
    )
    token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await result_future

    await runtime.stop()


@pytest.mark.asyncio
async def test_caller_loop() -> None:
    class MockChatCompletionClient(ChatCompletionClient):
        async def create(
            self,
            messages: Sequence[LLMMessage],
            *,
            tools: Sequence[Tool | ToolSchema] = [],
            json_output: Optional[bool] = None,
            extra_create_args: Mapping[str, Any] = {},
            cancellation_token: Optional[CancellationToken] = None,
        ) -> CreateResult:
            if len(messages) == 1:
                return CreateResult(
                    content=[FunctionCall(id="1", name="pass", arguments=json.dumps({"input": "test"}))],
                    finish_reason="stop",
                    usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                    cached=False,
                    logprobs=None,
                )
            return CreateResult(
                content="Done",
                finish_reason="stop",
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
                logprobs=None,
            )

        def create_stream(
            self,
            messages: Sequence[LLMMessage],
            *,
            tools: Sequence[Tool | ToolSchema] = [],
            json_output: Optional[bool] = None,
            extra_create_args: Mapping[str, Any] = {},
            cancellation_token: Optional[CancellationToken] = None,
        ) -> AsyncGenerator[Union[str, CreateResult], None]:
            raise NotImplementedError()

        def actual_usage(self) -> RequestUsage:
            return RequestUsage(prompt_tokens=0, completion_tokens=0)

        def total_usage(self) -> RequestUsage:
            return RequestUsage(prompt_tokens=0, completion_tokens=0)

        def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
            return 0

        def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
            return 0

        @property
        def capabilities(self) -> ModelCapabilities:
            return ModelCapabilities(vision=False, function_calling=True, json_output=False)

    client = MockChatCompletionClient()
    tools: List[Tool] = [FunctionTool(_pass_function, name="pass", description="Pass function")]
    runtime = SingleThreadedAgentRuntime()
    await ToolAgent.register(
        runtime,
        "tool_agent",
        lambda: ToolAgent(
            description="Tool agent",
            tools=tools,
        ),
    )
    agent = AgentId("tool_agent", "default")
    runtime.start()
    messages = await tool_agent_caller_loop(
        runtime, agent, client, [UserMessage(content="Hello", source="user")], tool_schema=tools
    )
    assert len(messages) == 3
    assert isinstance(messages[0], AssistantMessage)
    assert isinstance(messages[1], FunctionExecutionResultMessage)
    assert isinstance(messages[2], AssistantMessage)
    await runtime.stop()
