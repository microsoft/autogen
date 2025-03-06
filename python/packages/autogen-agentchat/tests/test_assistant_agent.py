import json
import logging
from typing import List

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff, TaskResult
from autogen_agentchat.messages import (
    ChatMessage,
    HandoffMessage,
    MemoryQueryEvent,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
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
    LLMMessage,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.models._model_client import ModelFamily
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.replay import ReplayChatCompletionClient
from utils import FileLogHandler

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_assistant_agent.log"))


def _pass_function(input: str) -> str:
    return "pass"


async def _fail_function(input: str) -> str:
    return "fail"


async def _echo_function(input: str) -> str:
    return input


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
        model_info={"function_calling": True, "vision": True, "json_output": True, "family": ModelFamily.GPT_4O},
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
        model_info={"function_calling": True, "vision": True, "json_output": True, "family": ModelFamily.GPT_4O},
    )
    agent = AssistantAgent(
        "tool_use_agent",
        model_client=model_client,
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
        reflect_on_tool_use=True,
    )
    result = await agent.run(task="task")

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
        model_info={"function_calling": True, "vision": True, "json_output": True, "family": ModelFamily.GPT_4O},
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
        model_info={"function_calling": True, "vision": True, "json_output": True, "family": ModelFamily.GPT_4O},
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
            )
        ],
        model_info={"function_calling": True, "vision": True, "json_output": True, "family": ModelFamily.GPT_4O},
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
    assert result.messages[3].content == handoff.message
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
async def test_invalid_model_capabilities() -> None:
    model = "random-model"
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key="",
        model_info={"vision": False, "function_calling": False, "json_output": False, "family": ModelFamily.UNKNOWN},
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
        model_info={"vision": False, "function_calling": False, "json_output": False, "family": ModelFamily.UNKNOWN},
    )
    model_client_2 = OpenAIChatCompletionClient(
        model=model,
        api_key="",
        model_info={"vision": True, "function_calling": False, "json_output": False, "family": ModelFamily.UNKNOWN},
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
    messages: List[ChatMessage] = [
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
        model_info={"function_calling": True, "vision": True, "json_output": True, "family": ModelFamily.GPT_4O},
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
            assert message.messages[-1].content == "Example response 2 to task"
            assert message.messages[1].content == [
                FunctionCall(id="1", name="_pass_function", arguments=r'{"input": "task"}'),
                FunctionCall(id="3", name="_echo_function", arguments=r'{"input": "task"}'),
            ]
            assert message.messages[2].content == [
                FunctionExecutionResult(call_id="1", content="pass", is_error=False, name="_pass_function"),
                FunctionExecutionResult(call_id="3", content="task", is_error=False, name="_echo_function"),
            ]
        elif isinstance(message, ModelClientStreamingChunkEvent):
            chunks.append(message.content)
    assert "".join(chunks) == "Example response 2 to task"
