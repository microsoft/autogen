import json
import logging
from typing import Dict, List

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff, TaskResult
from autogen_agentchat.messages import (
    BaseChatMessage,
    HandoffMessage,
    MemoryQueryEvent,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    StructuredMessage,
    TextMessage,
    ThoughtEvent,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from autogen_core import ComponentModel, FunctionCall, Image
from autogen_core.memory import ListMemory, Memory, MemoryContent, MemoryMimeType, MemoryQueryResult
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.models._model_client import ModelFamily, ModelInfo
from autogen_core.tools import BaseTool, FunctionTool, StaticWorkbench
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.replay import ReplayChatCompletionClient
from autogen_ext.tools.mcp import (
    McpWorkbench,
    SseServerParams,
)
from pydantic import BaseModel, ValidationError
from utils import FileLogHandler

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_assistant_agent.log"))


def _pass_function(input: str) -> str:
    return "pass"


async def _fail_function(input: str) -> str:
    return "fail"


async def _throw_function(input: str) -> str:
    raise ValueError("Helpful debugging information what went wrong.")


async def _echo_function(input: str) -> str:
    return input


@pytest.fixture
def model_info_all_capabilities() -> ModelInfo:
    return {
        "function_calling": True,
        "vision": True,
        "json_output": True,
        "family": ModelFamily.GPT_4O,
        "structured_output": True,
    }


@pytest.mark.asyncio
async def test_run_with_tool_call_summary_format_function(model_info_all_capabilities: ModelInfo) -> None:
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function"),
                    FunctionCall(id="2", arguments=json.dumps({"input": "task"}), name="_throw_function"),
                ],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass and fail function",
                cached=False,
            ),
        ],
        model_info=model_info_all_capabilities,
    )

    def conditional_string_templates(function_call: FunctionCall, function_call_result: FunctionExecutionResult) -> str:
        if not function_call_result.is_error:
            return "SUCCESS: {tool_name} with {arguments}"

        else:
            return "FAILURE: {result}"

    agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[_pass_function, _throw_function],
        tool_call_summary_format_fct=conditional_string_templates,
    )
    result = await agent.run(task="task")

    first_tool_call_summary = next((x for x in result.messages if isinstance(x, ToolCallSummaryMessage)), None)
    if first_tool_call_summary is None:
        raise AssertionError("Expected a ToolCallSummaryMessage but found none")

    assert (
        first_tool_call_summary.content
        == 'SUCCESS: _pass_function with {"input": "task"}\nFAILURE: Helpful debugging information what went wrong.'
    )


@pytest.mark.asyncio
async def test_run_with_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass function",
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
    )
    result = await agent.run(task="task")

    # Make sure the create call was made with the correct parameters.
    assert len(model_client.create_calls) == 1
    llm_messages = model_client.create_calls[0]["messages"]
    assert len(llm_messages) == 2
    assert isinstance(llm_messages[0], SystemMessage)
    assert llm_messages[0].content == agent._system_messages[0].content  # type: ignore
    assert isinstance(llm_messages[1], UserMessage)
    assert llm_messages[1].content == "task"

    assert len(result.messages) == 5
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ThoughtEvent)
    assert result.messages[1].content == "Calling pass function"
    assert isinstance(result.messages[2], ToolCallRequestEvent)
    assert result.messages[2].models_usage is not None
    assert result.messages[2].models_usage.completion_tokens == 5
    assert result.messages[2].models_usage.prompt_tokens == 10
    assert isinstance(result.messages[3], ToolCallExecutionEvent)
    assert result.messages[3].models_usage is None
    assert isinstance(result.messages[4], ToolCallSummaryMessage)
    assert result.messages[4].content == "pass"
    assert result.messages[4].models_usage is None

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
            index += 1

    # Test state saving and loading.
    state = await agent.save_state()
    agent2 = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
    )
    await agent2.load_state(state)
    state2 = await agent2.save_state()
    assert state == state2


@pytest.mark.asyncio
async def test_run_with_tools_and_reflection() -> None:
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="stop",
                content="Hello",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="stop",
                content="TERMINATE",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
        reflect_on_tool_use=True,
    )
    result = await agent.run(task="task")

    # Make sure the create call was made with the correct parameters.
    assert len(model_client.create_calls) == 2
    llm_messages = model_client.create_calls[0]["messages"]
    assert len(llm_messages) == 2
    assert isinstance(llm_messages[0], SystemMessage)
    assert llm_messages[0].content == agent._system_messages[0].content  # type: ignore
    assert isinstance(llm_messages[1], UserMessage)
    assert llm_messages[1].content == "task"
    llm_messages = model_client.create_calls[1]["messages"]
    assert len(llm_messages) == 4
    assert isinstance(llm_messages[0], SystemMessage)
    assert llm_messages[0].content == agent._system_messages[0].content  # type: ignore
    assert isinstance(llm_messages[1], UserMessage)
    assert llm_messages[1].content == "task"
    assert isinstance(llm_messages[2], AssistantMessage)
    assert isinstance(llm_messages[3], FunctionExecutionResultMessage)

    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert result.messages[1].models_usage is not None
    assert result.messages[1].models_usage.completion_tokens == 5
    assert result.messages[1].models_usage.prompt_tokens == 10
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    assert result.messages[2].models_usage is None
    assert isinstance(result.messages[3], TextMessage)
    assert result.messages[3].content == "Hello"
    assert result.messages[3].models_usage is not None
    assert result.messages[3].models_usage.completion_tokens == 5
    assert result.messages[3].models_usage.prompt_tokens == 10

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test state saving and loading.
    state = await agent.save_state()
    agent2 = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
    )
    await agent2.load_state(state)
    state2 = await agent2.save_state()
    assert state == state2


@pytest.mark.asyncio
async def test_run_with_parallel_tools() -> None:
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(id="1", arguments=json.dumps({"input": "task1"}), name="_pass_function"),
                    FunctionCall(id="2", arguments=json.dumps({"input": "task2"}), name="_pass_function"),
                    FunctionCall(id="3", arguments=json.dumps({"input": "task3"}), name="_echo_function"),
                ],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass and echo functions",
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
    )
    result = await agent.run(task="task")

    assert len(result.messages) == 5
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ThoughtEvent)
    assert result.messages[1].content == "Calling pass and echo functions"
    assert isinstance(result.messages[2], ToolCallRequestEvent)
    assert result.messages[2].content == [
        FunctionCall(id="1", arguments=r'{"input": "task1"}', name="_pass_function"),
        FunctionCall(id="2", arguments=r'{"input": "task2"}', name="_pass_function"),
        FunctionCall(id="3", arguments=r'{"input": "task3"}', name="_echo_function"),
    ]
    assert result.messages[2].models_usage is not None
    assert result.messages[2].models_usage.completion_tokens == 5
    assert result.messages[2].models_usage.prompt_tokens == 10
    assert isinstance(result.messages[3], ToolCallExecutionEvent)
    expected_content = [
        FunctionExecutionResult(call_id="1", content="pass", is_error=False, name="_pass_function"),
        FunctionExecutionResult(call_id="2", content="pass", is_error=False, name="_pass_function"),
        FunctionExecutionResult(call_id="3", content="task3", is_error=False, name="_echo_function"),
    ]
    for expected in expected_content:
        assert expected in result.messages[3].content
    assert result.messages[3].models_usage is None
    assert isinstance(result.messages[4], ToolCallSummaryMessage)
    assert result.messages[4].content == "pass\npass\ntask3"
    assert result.messages[4].models_usage is None

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
            index += 1

    # Test state saving and loading.
    state = await agent.save_state()
    agent2 = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
    )
    await agent2.load_state(state)
    state2 = await agent2.save_state()
    assert state == state2


@pytest.mark.asyncio
async def test_run_with_parallel_tools_with_empty_call_ids() -> None:
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(id="", arguments=json.dumps({"input": "task1"}), name="_pass_function"),
                    FunctionCall(id="", arguments=json.dumps({"input": "task2"}), name="_pass_function"),
                    FunctionCall(id="", arguments=json.dumps({"input": "task3"}), name="_echo_function"),
                ],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
    )
    result = await agent.run(task="task")

    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert result.messages[1].content == [
        FunctionCall(id="", arguments=r'{"input": "task1"}', name="_pass_function"),
        FunctionCall(id="", arguments=r'{"input": "task2"}', name="_pass_function"),
        FunctionCall(id="", arguments=r'{"input": "task3"}', name="_echo_function"),
    ]
    assert result.messages[1].models_usage is not None
    assert result.messages[1].models_usage.completion_tokens == 5
    assert result.messages[1].models_usage.prompt_tokens == 10
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    expected_content = [
        FunctionExecutionResult(call_id="", content="pass", is_error=False, name="_pass_function"),
        FunctionExecutionResult(call_id="", content="pass", is_error=False, name="_pass_function"),
        FunctionExecutionResult(call_id="", content="task3", is_error=False, name="_echo_function"),
    ]
    for expected in expected_content:
        assert expected in result.messages[2].content
    assert result.messages[2].models_usage is None
    assert isinstance(result.messages[3], ToolCallSummaryMessage)
    assert result.messages[3].content == "pass\npass\ntask3"
    assert result.messages[3].models_usage is None

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
            index += 1

    # Test state saving and loading.
    state = await agent.save_state()
    agent2 = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
    )
    await agent2.load_state(state)
    state2 = await agent2.save_state()
    assert state == state2


@pytest.mark.asyncio
async def test_run_with_workbench() -> None:
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="stop",
                content="Hello",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="stop",
                content="TERMINATE",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    workbench = StaticWorkbench(
        [
            FunctionTool(_pass_function, description="Pass"),
            FunctionTool(_fail_function, description="Fail"),
            FunctionTool(_echo_function, description="Echo"),
        ]
    )

    # Test raise error when both workbench and tools are provided.
    with pytest.raises(ValueError):
        AssistantAgent(
            "tool_use_agent",
            model_client=model_client,
            tools=[
                _pass_function,
                _fail_function,
                FunctionTool(_echo_function, description="Echo"),
            ],
            workbench=workbench,
        )

    agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        workbench=workbench,
        reflect_on_tool_use=True,
    )
    result = await agent.run(task="task")

    # Make sure the create call was made with the correct parameters.
    assert len(model_client.create_calls) == 2
    llm_messages = model_client.create_calls[0]["messages"]
    assert len(llm_messages) == 2
    assert isinstance(llm_messages[0], SystemMessage)
    assert llm_messages[0].content == agent._system_messages[0].content  # type: ignore
    assert isinstance(llm_messages[1], UserMessage)
    assert llm_messages[1].content == "task"
    llm_messages = model_client.create_calls[1]["messages"]
    assert len(llm_messages) == 4
    assert isinstance(llm_messages[0], SystemMessage)
    assert llm_messages[0].content == agent._system_messages[0].content  # type: ignore
    assert isinstance(llm_messages[1], UserMessage)
    assert llm_messages[1].content == "task"
    assert isinstance(llm_messages[2], AssistantMessage)
    assert isinstance(llm_messages[3], FunctionExecutionResultMessage)

    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert result.messages[1].models_usage is not None
    assert result.messages[1].models_usage.completion_tokens == 5
    assert result.messages[1].models_usage.prompt_tokens == 10
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    assert result.messages[2].models_usage is None
    assert isinstance(result.messages[3], TextMessage)
    assert result.messages[3].content == "Hello"
    assert result.messages[3].models_usage is not None
    assert result.messages[3].models_usage.completion_tokens == 5
    assert result.messages[3].models_usage.prompt_tokens == 10

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test state saving and loading.
    state = await agent.save_state()
    agent2 = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
    )
    await agent2.load_state(state)
    state2 = await agent2.save_state()
    assert state == state2


@pytest.mark.asyncio
async def test_output_format() -> None:
    class AgentResponse(BaseModel):
        response: str
        status: str

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content=AgentResponse(response="Hello", status="success").model_dump_json(),
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
        ]
    )
    agent = AssistantAgent(
        "test_agent",
        model_client=model_client,
        output_content_type=AgentResponse,
    )
    assert StructuredMessage[AgentResponse] in agent.produced_message_types
    assert TextMessage not in agent.produced_message_types

    result = await agent.run()
    assert len(result.messages) == 1
    assert isinstance(result.messages[0], StructuredMessage)
    assert isinstance(result.messages[0].content, AgentResponse)  # type: ignore[reportUnknownMemberType]
    assert result.messages[0].content.response == "Hello"
    assert result.messages[0].content.status == "success"

    # Test streaming.
    agent = AssistantAgent(
        "test_agent",
        model_client=model_client,
        model_client_stream=True,
        output_content_type=AgentResponse,
    )
    model_client.reset()
    stream = agent.run_stream()
    stream_result: TaskResult | None = None
    async for message in stream:
        if isinstance(message, TaskResult):
            stream_result = message
    assert stream_result is not None
    assert len(stream_result.messages) == 1
    assert isinstance(stream_result.messages[0], StructuredMessage)
    assert isinstance(stream_result.messages[0].content, AgentResponse)  # type: ignore[reportUnknownMemberType]
    assert stream_result.messages[0].content.response == "Hello"
    assert stream_result.messages[0].content.status == "success"


@pytest.mark.asyncio
async def test_reflection_output_format() -> None:
    class AgentResponse(BaseModel):
        response: str
        status: str

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            AgentResponse(response="Hello", status="success").model_dump_json(),
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = AssistantAgent(
        "test_agent",
        model_client=model_client,
        output_content_type=AgentResponse,
        # reflect_on_tool_use=True,
        tools=[
            _pass_function,
            _fail_function,
        ],
    )
    result = await agent.run()
    assert len(result.messages) == 3
    assert isinstance(result.messages[0], ToolCallRequestEvent)
    assert isinstance(result.messages[1], ToolCallExecutionEvent)
    assert isinstance(result.messages[2], StructuredMessage)
    assert isinstance(result.messages[2].content, AgentResponse)  # type: ignore[reportUnknownMemberType]
    assert result.messages[2].content.response == "Hello"
    assert result.messages[2].content.status == "success"

    # Test streaming.
    agent = AssistantAgent(
        "test_agent",
        model_client=model_client,
        model_client_stream=True,
        output_content_type=AgentResponse,
        # reflect_on_tool_use=True,
        tools=[
            _pass_function,
            _fail_function,
        ],
    )
    model_client.reset()
    stream = agent.run_stream()
    stream_result: TaskResult | None = None
    async for message in stream:
        if isinstance(message, TaskResult):
            stream_result = message
    assert stream_result is not None
    assert len(stream_result.messages) == 3
    assert isinstance(stream_result.messages[0], ToolCallRequestEvent)
    assert isinstance(stream_result.messages[1], ToolCallExecutionEvent)
    assert isinstance(stream_result.messages[2], StructuredMessage)
    assert isinstance(stream_result.messages[2].content, AgentResponse)  # type: ignore[reportUnknownMemberType]
    assert stream_result.messages[2].content.response == "Hello"
    assert stream_result.messages[2].content.status == "success"

    # Test when reflect_on_tool_use is False
    model_client.reset()
    agent = AssistantAgent(
        "test_agent",
        model_client=model_client,
        output_content_type=AgentResponse,
        reflect_on_tool_use=False,
        tools=[
            _pass_function,
            _fail_function,
        ],
    )
    result = await agent.run()
    assert len(result.messages) == 3
    assert isinstance(result.messages[0], ToolCallRequestEvent)
    assert isinstance(result.messages[1], ToolCallExecutionEvent)
    assert isinstance(result.messages[2], ToolCallSummaryMessage)


@pytest.mark.asyncio
async def test_handoffs() -> None:
    handoff = Handoff(target="agent2")
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(id="1", arguments=json.dumps({}), name=handoff.name),
                ],
                usage=RequestUsage(prompt_tokens=42, completion_tokens=43),
                cached=False,
                thought="Calling handoff function",
            )
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    tool_use_agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
        handoffs=[handoff],
    )
    assert HandoffMessage in tool_use_agent.produced_message_types
    result = await tool_use_agent.run(task="task")
    assert len(result.messages) == 5
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ThoughtEvent)
    assert result.messages[1].content == "Calling handoff function"
    assert isinstance(result.messages[2], ToolCallRequestEvent)
    assert result.messages[2].models_usage is not None
    assert result.messages[2].models_usage.completion_tokens == 43
    assert result.messages[2].models_usage.prompt_tokens == 42
    assert isinstance(result.messages[3], ToolCallExecutionEvent)
    assert result.messages[3].models_usage is None
    assert isinstance(result.messages[4], HandoffMessage)
    assert result.messages[4].content == handoff.message
    assert result.messages[4].target == handoff.target
    assert result.messages[4].models_usage is None
    assert result.messages[4].context == [AssistantMessage(content="Calling handoff function", source="tool_use_agent")]

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in tool_use_agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1


@pytest.mark.asyncio
async def test_handoff_with_tool_call_context() -> None:
    handoff = Handoff(target="agent2")
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(id="1", arguments=json.dumps({}), name=handoff.name),
                    FunctionCall(id="2", arguments=json.dumps({"input": "task"}), name="_pass_function"),
                ],
                usage=RequestUsage(prompt_tokens=42, completion_tokens=43),
                cached=False,
                thought="Calling handoff function",
            )
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    tool_use_agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
        handoffs=[handoff],
    )
    assert HandoffMessage in tool_use_agent.produced_message_types
    result = await tool_use_agent.run(task="task")
    assert len(result.messages) == 5
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ThoughtEvent)
    assert result.messages[1].content == "Calling handoff function"
    assert isinstance(result.messages[2], ToolCallRequestEvent)
    assert result.messages[2].models_usage is not None
    assert result.messages[2].models_usage.completion_tokens == 43
    assert result.messages[2].models_usage.prompt_tokens == 42
    assert isinstance(result.messages[3], ToolCallExecutionEvent)
    assert result.messages[3].models_usage is None
    assert isinstance(result.messages[4], HandoffMessage)
    assert result.messages[4].content == handoff.message
    assert result.messages[4].target == handoff.target
    assert result.messages[4].models_usage is None
    assert result.messages[4].context == [
        AssistantMessage(
            content=[FunctionCall(id="2", arguments=r'{"input": "task"}', name="_pass_function")],
            source="tool_use_agent",
            thought="Calling handoff function",
        ),
        FunctionExecutionResultMessage(
            content=[FunctionExecutionResult(call_id="2", content="pass", is_error=False, name="_pass_function")]
        ),
    ]

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in tool_use_agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1


@pytest.mark.asyncio
async def test_custom_handoffs() -> None:
    name = "transfer_to_agent2"
    description = "Handoff to agent2."
    next_action = "next_action"

    class TextCommandHandOff(Handoff):
        @property
        def handoff_tool(self) -> BaseTool[BaseModel, BaseModel]:
            """Create a handoff tool from this handoff configuration."""

            def _next_action(action: str) -> str:
                """Returns the action you want the user to perform"""
                return action

            return FunctionTool(_next_action, name=self.name, description=self.description, strict=True)

    handoff = TextCommandHandOff(name=name, description=description, target="agent2")
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(id="1", arguments=json.dumps({"action": next_action}), name=handoff.name),
                ],
                usage=RequestUsage(prompt_tokens=42, completion_tokens=43),
                cached=False,
            )
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    tool_use_agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
        handoffs=[handoff],
    )
    assert HandoffMessage in tool_use_agent.produced_message_types
    result = await tool_use_agent.run(task="task")
    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert result.messages[1].models_usage is not None
    assert result.messages[1].models_usage.completion_tokens == 43
    assert result.messages[1].models_usage.prompt_tokens == 42
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    assert result.messages[2].models_usage is None
    assert isinstance(result.messages[3], HandoffMessage)
    assert result.messages[3].content == next_action
    assert result.messages[3].target == handoff.target

    assert result.messages[3].models_usage is None

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in tool_use_agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1


@pytest.mark.asyncio
async def test_custom_object_handoffs() -> None:
    """test handoff tool return a object"""
    name = "transfer_to_agent2"
    description = "Handoff to agent2."
    next_action = {"action": "next_action"}  # using a map, not a str

    class DictCommandHandOff(Handoff):
        @property
        def handoff_tool(self) -> BaseTool[BaseModel, BaseModel]:
            """Create a handoff tool from this handoff configuration."""

            def _next_action(action: str) -> Dict[str, str]:
                """Returns the action you want the user to perform"""
                return {"action": action}

            return FunctionTool(_next_action, name=self.name, description=self.description, strict=True)

    handoff = DictCommandHandOff(name=name, description=description, target="agent2")
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(id="1", arguments=json.dumps({"action": "next_action"}), name=handoff.name),
                ],
                usage=RequestUsage(prompt_tokens=42, completion_tokens=43),
                cached=False,
            )
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    tool_use_agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
        handoffs=[handoff],
    )
    assert HandoffMessage in tool_use_agent.produced_message_types
    result = await tool_use_agent.run(task="task")
    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert result.messages[1].models_usage is not None
    assert result.messages[1].models_usage.completion_tokens == 43
    assert result.messages[1].models_usage.prompt_tokens == 42
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    assert result.messages[2].models_usage is None
    assert isinstance(result.messages[3], HandoffMessage)
    # the content will return as a string, because the function call will convert to string
    assert result.messages[3].content == str(next_action)
    assert result.messages[3].target == handoff.target

    assert result.messages[3].models_usage is None

    # Test streaming.
    model_client.reset()
    index = 0
    async for message in tool_use_agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1


@pytest.mark.asyncio
async def test_multi_modal_task(monkeypatch: pytest.MonkeyPatch) -> None:
    model_client = ReplayChatCompletionClient(["Hello"])
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
    )
    # Generate a random base64 image.
    img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
    result = await agent.run(task=MultiModalMessage(source="user", content=["Test", Image.from_base64(img_base64)]))
    assert len(result.messages) == 2


@pytest.mark.asyncio
async def test_run_with_structured_task() -> None:
    class InputTask(BaseModel):
        input: str
        data: List[str]

    model_client = ReplayChatCompletionClient(["Hello"])
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
    )

    task = StructuredMessage[InputTask](content=InputTask(input="Test", data=["Test1", "Test2"]), source="user")
    result = await agent.run(task=task)
    assert len(result.messages) == 2


@pytest.mark.asyncio
async def test_invalid_model_capabilities() -> None:
    model = "random-model"
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="",
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False,
        },
    )

    with pytest.raises(ValueError):
        agent = AssistantAgent(
            name="assistant",
            model_client=model_client,
            tools=[
                _pass_function,
                _fail_function,
                FunctionTool(_echo_function, description="Echo"),
            ],
        )
        await agent.run(task=TextMessage(source="user", content="Test"))

    with pytest.raises(ValueError):
        agent = AssistantAgent(name="assistant", model_client=model_client, handoffs=["agent2"])
        await agent.run(task=TextMessage(source="user", content="Test"))


@pytest.mark.asyncio
async def test_remove_images() -> None:
    model = "random-model"
    model_client_1 = OpenAIChatCompletionClient(
        model=model,
        api_key="",
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False,
        },
    )
    model_client_2 = OpenAIChatCompletionClient(
        model=model,
        api_key="",
        model_info={
            "vision": True,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False,
        },
    )

    img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
    messages: List[LLMMessage] = [
        SystemMessage(content="System.1"),
        UserMessage(content=["User.1", Image.from_base64(img_base64)], source="user.1"),
        AssistantMessage(content="Assistant.1", source="assistant.1"),
        UserMessage(content="User.2", source="assistant.2"),
    ]

    agent_1 = AssistantAgent(name="assistant_1", model_client=model_client_1)
    result = agent_1._get_compatible_context(model_client_1, messages)  # type: ignore
    assert len(result) == 4
    assert isinstance(result[1].content, str)

    agent_2 = AssistantAgent(name="assistant_2", model_client=model_client_2)
    result = agent_2._get_compatible_context(model_client_2, messages)  # type: ignore
    assert len(result) == 4
    assert isinstance(result[1].content, list)


@pytest.mark.asyncio
async def test_list_chat_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content="Response to message 1",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ]
    )
    agent = AssistantAgent(
        "test_agent",
        model_client=model_client,
    )

    # Create a list of chat messages
    messages: List[BaseChatMessage] = [
        TextMessage(content="Message 1", source="user"),
        TextMessage(content="Message 2", source="user"),
    ]

    # Test run method with list of messages
    result = await agent.run(task=messages)
    assert len(result.messages) == 3  # 2 input messages + 1 response message
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Message 1"
    assert result.messages[0].source == "user"
    assert isinstance(result.messages[1], TextMessage)
    assert result.messages[1].content == "Message 2"
    assert result.messages[1].source == "user"
    assert isinstance(result.messages[2], TextMessage)
    assert result.messages[2].content == "Response to message 1"
    assert result.messages[2].source == "test_agent"
    assert result.messages[2].models_usage is not None
    assert result.messages[2].models_usage.completion_tokens == 5
    assert result.messages[2].models_usage.prompt_tokens == 10

    # Test run_stream method with list of messages
    model_client.reset()  # Reset the mock client
    index = 0
    async for message in agent.run_stream(task=messages):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1


@pytest.mark.asyncio
async def test_model_context(monkeypatch: pytest.MonkeyPatch) -> None:
    model_client = ReplayChatCompletionClient(["Response to message 3"])
    model_context = BufferedChatCompletionContext(buffer_size=2)
    agent = AssistantAgent(
        "test_agent",
        model_client=model_client,
        model_context=model_context,
    )

    messages = [
        TextMessage(content="Message 1", source="user"),
        TextMessage(content="Message 2", source="user"),
        TextMessage(content="Message 3", source="user"),
    ]
    await agent.run(task=messages)

    # Check that the model_context property returns the correct internal context
    assert agent.model_context == model_context
    # Check if the mock client is called with only the last two messages.
    assert len(model_client.create_calls) == 1
    # 2 message from the context + 1 system message
    assert len(model_client.create_calls[0]["messages"]) == 3


@pytest.mark.asyncio
async def test_run_with_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    model_client = ReplayChatCompletionClient(["Hello"])
    b64_image_str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"

    # Test basic memory properties and empty context
    memory = ListMemory(name="test_memory")
    assert memory.name == "test_memory"

    empty_context = BufferedChatCompletionContext(buffer_size=2)
    empty_results = await memory.update_context(empty_context)
    assert len(empty_results.memories.results) == 0

    # Test various content types
    memory = ListMemory()
    await memory.add(MemoryContent(content="text content", mime_type=MemoryMimeType.TEXT))
    await memory.add(MemoryContent(content={"key": "value"}, mime_type=MemoryMimeType.JSON))
    await memory.add(MemoryContent(content=Image.from_base64(b64_image_str), mime_type=MemoryMimeType.IMAGE))

    # Test query functionality
    query_result = await memory.query(MemoryContent(content="", mime_type=MemoryMimeType.TEXT))
    assert isinstance(query_result, MemoryQueryResult)
    # Should have all three memories we added
    assert len(query_result.results) == 3

    # Test clear and cleanup
    await memory.clear()
    empty_query = await memory.query(MemoryContent(content="", mime_type=MemoryMimeType.TEXT))
    assert len(empty_query.results) == 0
    await memory.close()  # Should not raise

    # Test invalid memory type
    with pytest.raises(TypeError):
        AssistantAgent(
            "test_agent",
            model_client=model_client,
            memory="invalid",  # type: ignore
        )

    # Test with agent
    memory2 = ListMemory()
    await memory2.add(MemoryContent(content="test instruction", mime_type=MemoryMimeType.TEXT))

    agent = AssistantAgent("test_agent", model_client=model_client, memory=[memory2])

    # Test dump and load component with memory
    agent_config: ComponentModel = agent.dump_component()
    assert agent_config.provider == "autogen_agentchat.agents.AssistantAgent"
    agent2 = AssistantAgent.load_component(agent_config)

    result = await agent2.run(task="test task")
    assert len(result.messages) > 0
    memory_event = next((msg for msg in result.messages if isinstance(msg, MemoryQueryEvent)), None)
    assert memory_event is not None
    assert len(memory_event.content) > 0
    assert isinstance(memory_event.content[0], MemoryContent)

    # Test memory protocol
    class BadMemory:
        pass

    assert not isinstance(BadMemory(), Memory)
    assert isinstance(ListMemory(), Memory)


@pytest.mark.asyncio
async def test_assistant_agent_declarative() -> None:
    model_client = ReplayChatCompletionClient(
        ["Response to message 3"],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    model_context = BufferedChatCompletionContext(buffer_size=2)
    agent = AssistantAgent(
        "test_agent",
        model_client=model_client,
        model_context=model_context,
        memory=[ListMemory(name="test_memory")],
    )

    agent_config: ComponentModel = agent.dump_component()
    assert agent_config.provider == "autogen_agentchat.agents.AssistantAgent"

    agent2 = AssistantAgent.load_component(agent_config)
    assert agent2.name == agent.name

    agent3 = AssistantAgent(
        "test_agent",
        model_client=model_client,
        model_context=model_context,
        tools=[
            _pass_function,
            _fail_function,
            FunctionTool(_echo_function, description="Echo"),
        ],
    )
    agent3_config = agent3.dump_component()
    assert agent3_config.provider == "autogen_agentchat.agents.AssistantAgent"


@pytest.mark.asyncio
async def test_model_client_stream() -> None:
    mock_client = ReplayChatCompletionClient(
        [
            "Response to message 3",
        ]
    )
    agent = AssistantAgent(
        "test_agent",
        model_client=mock_client,
        model_client_stream=True,
    )
    chunks: List[str] = []
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert isinstance(message.messages[-1], TextMessage)
            assert message.messages[-1].content == "Response to message 3"
        elif isinstance(message, ModelClientStreamingChunkEvent):
            chunks.append(message.content)
    assert "".join(chunks) == "Response to message 3"


@pytest.mark.asyncio
async def test_model_client_stream_with_tool_calls() -> None:
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                content=[
                    FunctionCall(id="1", name="_pass_function", arguments=r'{"input": "task"}'),
                    FunctionCall(id="3", name="_echo_function", arguments=r'{"input": "task"}'),
                ],
                finish_reason="function_calls",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            "Example response 2 to task",
        ]
    )
    mock_client._model_info["function_calling"] = True  # pyright: ignore
    agent = AssistantAgent(
        "test_agent",
        model_client=mock_client,
        model_client_stream=True,
        reflect_on_tool_use=True,
        tools=[_pass_function, _echo_function],
    )
    chunks: List[str] = []
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert isinstance(message.messages[-1], TextMessage)
            assert isinstance(message.messages[1], ToolCallRequestEvent)
            assert message.messages[-1].content == "Example response 2 to task"
            assert message.messages[1].content == [
                FunctionCall(id="1", name="_pass_function", arguments=r'{"input": "task"}'),
                FunctionCall(id="3", name="_echo_function", arguments=r'{"input": "task"}'),
            ]
            assert isinstance(message.messages[2], ToolCallExecutionEvent)
            assert message.messages[2].content == [
                FunctionExecutionResult(call_id="1", content="pass", is_error=False, name="_pass_function"),
                FunctionExecutionResult(call_id="3", content="task", is_error=False, name="_echo_function"),
            ]
        elif isinstance(message, ModelClientStreamingChunkEvent):
            chunks.append(message.content)
    assert "".join(chunks) == "Example response 2 to task"


@pytest.mark.asyncio
async def test_invalid_structured_output_format() -> None:
    class AgentResponse(BaseModel):
        response: str
        status: str

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content='{"response": "Hello"}',
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
        ]
    )

    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        output_content_type=AgentResponse,
    )

    with pytest.raises(ValidationError):
        await agent.run()


@pytest.mark.asyncio
async def test_structured_message_factory_serialization() -> None:
    class AgentResponse(BaseModel):
        result: str
        status: str

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content=AgentResponse(result="All good", status="ok").model_dump_json(),
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ]
    )

    agent = AssistantAgent(
        name="structured_agent",
        model_client=model_client,
        output_content_type=AgentResponse,
        output_content_type_format="{result} - {status}",
    )

    dumped = agent.dump_component()
    restored_agent = AssistantAgent.load_component(dumped)
    result = await restored_agent.run()

    assert isinstance(result.messages[0], StructuredMessage)
    assert result.messages[0].content.result == "All good"  # type: ignore[reportUnknownMemberType]
    assert result.messages[0].content.status == "ok"  # type: ignore[reportUnknownMemberType]


@pytest.mark.asyncio
async def test_structured_message_format_string() -> None:
    class AgentResponse(BaseModel):
        field1: str
        field2: str

    expected = AgentResponse(field1="foo", field2="bar")

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content=expected.model_dump_json(),
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ]
    )

    agent = AssistantAgent(
        name="formatted_agent",
        model_client=model_client,
        output_content_type=AgentResponse,
        output_content_type_format="{field1} - {field2}",
    )

    result = await agent.run()

    assert len(result.messages) == 1
    message = result.messages[0]

    # Check that it's a StructuredMessage with the correct content model
    assert isinstance(message, StructuredMessage)
    assert isinstance(message.content, AgentResponse)  # type: ignore[reportUnknownMemberType]
    assert message.content == expected

    # Check that the format_string was applied correctly
    assert message.to_model_text() == "foo - bar"


@pytest.mark.asyncio
async def test_tools_serialize_and_deserialize() -> None:
    def test() -> str:
        return "hello world"

    client = OpenAIChatCompletionClient(
        model="gpt-4o",
        api_key="API_KEY",
    )

    agent = AssistantAgent(
        name="test",
        model_client=client,
        tools=[test],
    )

    serialize = agent.dump_component()
    deserialize = AssistantAgent.load_component(serialize)

    assert deserialize.name == agent.name
    assert await deserialize._workbench.list_tools() == await agent._workbench.list_tools()  # type: ignore


@pytest.mark.asyncio
async def test_workbenchs_serialize_and_deserialize() -> None:
    workbench = McpWorkbench(server_params=SseServerParams(url="http://test-url"))

    client = OpenAIChatCompletionClient(
        model="gpt-4o",
        api_key="API_KEY",
    )

    agent = AssistantAgent(
        name="test",
        model_client=client,
        workbench=workbench,
    )

    serialize = agent.dump_component()
    deserialize = AssistantAgent.load_component(serialize)

    assert deserialize.name == agent.name
    assert deserialize._workbench._to_config() == agent._workbench._to_config()  # type: ignore


@pytest.mark.asyncio
async def test_tools_deserialize_aware() -> None:
    dump = """
    {
        "provider": "autogen_agentchat.agents.AssistantAgent",
        "component_type": "agent",
        "version": 1,
        "component_version": 1,
        "description": "An agent that provides assistance with tool use.",
        "label": "AssistantAgent",
        "config": {
            "name": "TestAgent",
            "model_client":{
                "provider": "autogen_ext.models.replay.ReplayChatCompletionClient",
                "component_type": "replay_chat_completion_client",
                "version": 1,
                "component_version": 1,
                "description": "A mock chat completion client that replays predefined responses using an index-based approach.",
                "label": "ReplayChatCompletionClient",
                "config": {
                    "chat_completions": [
                        {
                            "finish_reason": "function_calls",
                            "content": [
                                {
                                    "id": "hello",
                                    "arguments": "{}",
                                    "name": "hello"
                                }
                            ],
                            "usage": {
                                "prompt_tokens": 0,
                                "completion_tokens": 0
                            },
                            "cached": false
                        }
                    ],
                    "model_info": {
                        "vision": false,
                        "function_calling": true,
                        "json_output": false,
                        "family": "unknown",
                        "structured_output": false
                    }
                }
            },
            "tools": [
                {
                    "provider": "autogen_core.tools.FunctionTool",
                    "component_type": "tool",
                    "version": 1,
                    "component_version": 1,
                    "description": "Create custom tools by wrapping standard Python functions.",
                    "label": "FunctionTool",
                    "config": {
                        "source_code": "def hello():\\n    return 'Hello, World!'\\n",
                        "name": "hello",
                        "description": "",
                        "global_imports": [],
                        "has_cancellation_support": false
                    }
                }
            ],
            "model_context": {
                "provider": "autogen_core.model_context.UnboundedChatCompletionContext",
                "component_type": "chat_completion_context",
                "version": 1,
                "component_version": 1,
                "description": "An unbounded chat completion context that keeps a view of the all the messages.",
                "label": "UnboundedChatCompletionContext",
                "config": {}
            },
            "description": "An agent that provides assistance with ability to use tools.",
            "system_message": "You are a helpful assistant.",
            "model_client_stream": false,
            "reflect_on_tool_use": false,
            "tool_call_summary_format": "{result}",
            "metadata": {}
        }
    }
    """
    agent = AssistantAgent.load_component(json.loads(dump))
    result = await agent.run(task="hello")

    assert len(result.messages) == 4
    assert result.messages[-1].content == "Hello, World!"  # type: ignore
    assert result.messages[-1].type == "ToolCallSummaryMessage"  # type: ignore
    assert isinstance(result.messages[-1], ToolCallSummaryMessage)  # type: ignore
