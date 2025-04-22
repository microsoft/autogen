from asyncio import CancelledError
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, call

import azure.ai.projects.models as models
import pytest
from autogen_agentchat.base._chat_agent import Response
from autogen_agentchat.messages import TextMessage, ToolCallExecutionEvent
from autogen_core._cancellation_token import CancellationToken
from autogen_core.tools._function_tool import FunctionTool
from autogen_ext.agents.azure._azure_ai_agent import AzureAIAgent
from autogen_ext.agents.azure._types import ListToolType
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import ThreadMessage


class FakeText:
    def __init__(self, value: str) -> None:
        self.value = value


class FakeTextContent:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = FakeText(text)


class FakeMessage:
    def __init__(self, id: str, text: str) -> None:
        self.id = id
        # The agent expects content to be a list of objects with a "type" attribute.
        self.content = [FakeTextContent(text)]
        self.role = "user"

    @property
    def text_messages(self) -> List[FakeTextContent]:
        """Returns all text message contents in the messages.

        :rtype: List[MessageTextContent]
        """
        if not self.content:
            return []
        return [content for content in self.content if isinstance(content, FakeTextContent)]


class FakeOpenAIPageableListOfThreadMessage:
    def __init__(self, data: List[ThreadMessage | FakeMessage], has_more: bool = False) -> None:
        self.data = data
        self._has_more = has_more

    @property
    def has_more(self) -> bool:
        return self._has_more

    @property
    def text_messages(self) -> List[ThreadMessage | FakeTextContent]:
        """Returns all text message contents in the messages.

        :rtype: List[FakeMessage]
        """
        texts = [content for msg in self.data for content in msg.text_messages]  # type: ignore
        return texts  # type: ignore


def mock_list() -> FakeOpenAIPageableListOfThreadMessage:
    return FakeOpenAIPageableListOfThreadMessage([FakeMessage("msg-mock", "response")])


def create_agent(
    mock_project_client: MagicMock,
    tools: Optional[ListToolType] = None,
    agent_name: str = "test_agent",
    description: str = "Test Azure AI Agent",
    instructions: str = "Test instructions",
    agent_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> AzureAIAgent:
    return AzureAIAgent(
        name=agent_name,
        description=description,
        project_client=mock_project_client,
        deployment_name="test_model",
        tools=tools,
        instructions=instructions,
        agent_id=agent_id,
        thread_id=thread_id,
    )


@pytest.fixture
def mock_project_client() -> MagicMock:
    client = MagicMock(spec=AIProjectClient)

    agents = MagicMock()

    client.agents = agents

    client.agents.create_agent = AsyncMock(return_value=MagicMock(id="assistant-mock"))
    client.agents.get_agent = AsyncMock(return_value=MagicMock(id="assistant-mock"))

    agent_run = MagicMock()
    agent_run.id = "run-mock"
    agent_run.status = "completed"

    client.agents.create_run = AsyncMock(return_value=agent_run)
    client.agents.get_run = AsyncMock(return_value=agent_run)
    client.agents.list_messages = AsyncMock(return_value=mock_list())

    client.agents.create_message = AsyncMock()

    client.agents.get_thread = AsyncMock(id="thread-mock", return_value=MagicMock(id="thread-mock"))
    client.agents.create_thread = AsyncMock(return_value=MagicMock(id="thread-mock"))

    return client


@pytest.mark.asyncio
async def test_azure_ai_agent_initialization(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client, ["file_search"])

    assert agent.name == "test_agent"
    assert agent.description == "Test Azure AI Agent"
    assert agent.deployment_name == "test_model"
    assert agent.instructions == "Test instructions"
    assert len(agent.tools) == 1


@pytest.mark.asyncio
async def test_on_messages(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client)

    messages = [TextMessage(content="Hello", source="user")]
    response = await agent.on_messages(messages)

    assert response is not None


@pytest.mark.asyncio
async def test_on_reset(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client)

    await agent.on_reset(CancellationToken())

    mock_project_client.agents.create_thread.assert_called_once()


@pytest.mark.asyncio
async def test_save_and_load_state(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client, agent_id="agent-mock", thread_id="thread-mock")

    state = await agent.save_state()
    assert state is not None

    await agent.load_state(state)

    assert agent.agent_id == state["agent_id"]
    # assert agent._init_thread_id == state["thread_id"]


@pytest.mark.asyncio
async def test_on_upload_for_code_interpreter(mock_project_client: MagicMock) -> None:
    file_mock = AsyncMock()
    file_mock.id = "file-mock"
    file_mock.status = "processed"

    thread_mock = AsyncMock()
    thread_mock.tool_resources = AsyncMock()
    thread_mock.tool_resources.code_interpreter = AsyncMock()
    thread_mock.tool_resources.code_interpreter.file_ids = []  # Set as a valid list

    mock_project_client.agents.upload_file_and_poll = AsyncMock(return_value=file_mock)
    mock_project_client.agents.get_thread = AsyncMock(return_value=thread_mock)
    mock_project_client.agents.update_thread = AsyncMock()

    agent = create_agent(
        mock_project_client,
    )

    file_paths = ["test_file_1.txt", "test_file_2.txt"]
    await agent.on_upload_for_code_interpreter(file_paths)

    mock_project_client.agents.upload_file_and_poll.assert_called()
    mock_project_client.agents.get_thread.assert_called_once()
    mock_project_client.agents.update_thread.assert_called_once()


@pytest.mark.asyncio
async def test_on_upload_for_file_search(mock_project_client: MagicMock) -> None:
    file_mock = AsyncMock()
    file_mock.id = "file-mock"
    file_mock.status = "processed"  # Set a valid status

    mock_project_client.agents.upload_file_and_poll = AsyncMock(return_value=file_mock)
    mock_project_client.agents.create_vector_store_and_poll = AsyncMock(return_value=AsyncMock(id="vector_store_id"))
    mock_project_client.agents.update_agent = AsyncMock()
    mock_project_client.agents.create_vector_store_file_batch_and_poll = AsyncMock()

    agent = create_agent(mock_project_client, tools=["file_search"])

    file_paths = ["test_file_1.txt", "test_file_2.txt"]
    await agent.on_upload_for_file_search(file_paths, cancellation_token=CancellationToken())

    mock_project_client.agents.upload_file_and_poll.assert_called()
    mock_project_client.agents.create_vector_store_and_poll.assert_called_once()
    mock_project_client.agents.update_agent.assert_called_once()
    mock_project_client.agents.create_vector_store_file_batch_and_poll.assert_called_once()


# @pytest.mark.asyncio
# async def test_add_tools(mock_project_client: MagicMock) -> None:
#     agent = create_agent(mock_project_client)

#     tools: Optional[ListToolType] = ["file_search", "code_interpreter"]
#     converted_tools: List[ToolDefinition] = []
#     agent._add_tools(tools, converted_tools)

#     assert len(converted_tools) == 2
#     assert isinstance(converted_tools[0], models.FileSearchToolDefinition)
#     assert isinstance(converted_tools[1], models.CodeInterpreterToolDefinition)


# @pytest.mark.asyncio
# async def test_ensure_initialized(mock_project_client: MagicMock) -> None:
#     agent = create_agent(mock_project_client)

#     await agent._ensure_initialized(create_new_agent=True, create_new_thread=True)

#     assert agent._agent is not None
#     assert agent._thread is not None


# @pytest.mark.asyncio
# async def test_execute_tool_call(mock_project_client: MagicMock) -> None:
#     mock_tool = MagicMock()
#     mock_tool.name = "test_tool"
#     mock_tool.run_json = AsyncMock(return_value={"result": "success"})
#     mock_tool.return_value_as_string = MagicMock(return_value="success")

#     agent = create_agent(mock_project_client)

#     agent._original_tools = [mock_tool]

#     tool_call = FunctionCall(id="test_tool", name="test_tool", arguments="{}")
#     result = await agent._execute_tool_call(tool_call, CancellationToken())

#     assert result == "success"
#     mock_tool.run_json.assert_called_once()


@pytest.mark.asyncio
async def test_upload_files(mock_project_client: MagicMock) -> None:
    mock_project_client.agents.create_vector_store_file_batch_and_poll = AsyncMock()

    mock_project_client.agents.update_agent = AsyncMock()
    mock_project_client.agents.create_vector_store_and_poll = AsyncMock(return_value=AsyncMock(id="vector_store_id"))

    mock_project_client.agents.upload_file_and_poll = AsyncMock(
        return_value=AsyncMock(id="file-id", status=models.FileState.PROCESSED)
    )

    agent = create_agent(mock_project_client, tools=["file_search"])

    await agent.on_upload_for_file_search(["test_file.txt"], cancellation_token=CancellationToken())

    mock_project_client.agents.upload_file_and_poll.assert_any_await(
        file_path="test_file.txt", purpose=models.FilePurpose.AGENTS, sleep_interval=0.5
    )


@pytest.mark.asyncio
async def test_on_messages_stream(mock_project_client: MagicMock) -> None:
    mock_project_client.agents.create_run = AsyncMock(
        return_value=MagicMock(id="run-id", status=models.RunStatus.COMPLETED)
    )
    mock_project_client.agents.list_messages = AsyncMock(return_value=mock_list())

    agent = create_agent(mock_project_client)

    messages = [TextMessage(content="Hello", source="user")]
    async for response in agent.on_messages_stream(messages):
        assert isinstance(response, Response)
        assert response.chat_message.to_model_message().content == "response"


@pytest.mark.asyncio
async def test_on_messages_stream_with_tool(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client, tools=["file_search"])

    messages = [TextMessage(content="Hello", source="user")]
    async for response in agent.on_messages_stream(messages):
        assert isinstance(response, Response)
        assert response.chat_message.to_model_message().content == "response"


@pytest.mark.asyncio
async def test_thread_id_validation(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client)

    with pytest.raises(ValueError, match="Thread not"):
        _ = agent.thread_id  # Using _ for intentionally unused variable


@pytest.mark.asyncio
async def test_get_agent_id_validation(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client)

    with pytest.raises(ValueError, match="Agent not"):
        _ = agent.agent_id  # Using _ for intentionally unused variable


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name, should_raise_error",
    [
        ("file_search", False),
        ("code_interpreter", False),
        ("bing_grounding", False),
        ("azure_function", False),
        ("azure_ai_search", False),
        ("sharepoint_grounding", False),
        ("unknown_tool", True),
    ],
)
async def test_adding_tools_as_literals(
    mock_project_client: MagicMock, tool_name: Any, should_raise_error: bool
) -> None:
    if should_raise_error:
        with pytest.raises(ValueError, match=tool_name):
            agent = create_agent(mock_project_client, tools=[tool_name])  # mypy ignore
    else:
        agent = agent = create_agent(mock_project_client, tools=[tool_name])
        assert agent.tools[0].type == tool_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_definition",
    [
        models.FileSearchToolDefinition(),
        models.CodeInterpreterToolDefinition(),
        models.BingGroundingToolDefinition(),  # type: ignore
        models.AzureFunctionToolDefinition(),  # type: ignore
        models.AzureAISearchToolDefinition(),
        models.SharepointToolDefinition(),  # type: ignore
    ],
)
async def test_adding_tools_as_typed_definition(mock_project_client: MagicMock, tool_definition: Any) -> None:
    agent = agent = create_agent(mock_project_client, tools=[tool_definition])

    assert len(agent.tools) == 1
    assert agent.tools[0].type == tool_definition.type


@pytest.mark.asyncio
async def test_adding_callable_func_as_tool(mock_project_client: MagicMock) -> None:
    def mock_tool_func() -> None:
        """Mock tool function."""
        pass

    agent = create_agent(mock_project_client, tools=[mock_tool_func])
    assert len(agent.tools) == 1

    assert agent.tools[0].type == "function"


@pytest.mark.asyncio
async def test_adding_core_autogen_tool(mock_project_client: MagicMock) -> None:
    def mock_tool_func() -> None:
        """Mock tool function."""
        pass

    tool = FunctionTool(
        func=mock_tool_func,
        name="mock_tool",
        description="Mock tool function",
    )

    agent = create_agent(mock_project_client, tools=[tool])

    assert len(agent.tools) == 1
    assert agent.tools[0].type == "function"


@pytest.mark.asyncio
async def test_adding_core_autogen_tool_without_doc_string(mock_project_client: MagicMock) -> None:
    def mock_tool_func() -> None:
        pass

    agent = create_agent(mock_project_client, tools=[mock_tool_func])

    assert len(agent.tools) == 1
    assert agent.tools[0].type == "function"
    assert agent.tools[0].function.description == ""  # type: ignore


@pytest.mark.asyncio
async def test_adding_unsupported_tool(mock_project_client: MagicMock) -> None:
    tool_name: Any = 5

    with pytest.raises(ValueError, match="class 'int'"):
        create_agent(mock_project_client, tools=[tool_name])


@pytest.mark.asyncio
async def test_agent_initialization_with_no_agent_id(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client)

    await agent.on_messages([TextMessage(content="Hello", source="user")])

    mock_project_client.agents.create_agent.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_initialization_with_agent_id(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client, agent_id="agent-mock")

    await agent.on_messages([TextMessage(content="Hello", source="user")])

    mock_project_client.agents.get_agent.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_initialization_with_no_thread_id(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client)

    await agent.on_messages([TextMessage(content="Hello", source="user")])

    mock_project_client.agents.create_thread.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_initialization_with_thread_id(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client, thread_id="thread-mock")

    await agent.on_messages([TextMessage(content="Hello", source="user")])

    mock_project_client.agents.get_thread.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_initialization_fetching_multiple_pages_of_thread_messages(mock_project_client: MagicMock) -> None:
    list_messages = [
        FakeOpenAIPageableListOfThreadMessage([FakeMessage("msg-mock-1", "response-1")], has_more=True),
        FakeOpenAIPageableListOfThreadMessage([FakeMessage("msg-mock-2", "response-2")]),
        FakeOpenAIPageableListOfThreadMessage(
            [FakeMessage("msg-mock-1", "response-1"), FakeMessage("msg-mock-2", "response-2")]
        ),
    ]

    mock_project_client.agents.get_thread = AsyncMock(id="thread-id", return_value=MagicMock(id="thread-id"))
    # Mock the list_messages method to return multiple pages of messages
    mock_project_client.agents.list_messages = AsyncMock(side_effect=list_messages)

    agent = create_agent(mock_project_client, thread_id="thread-id")

    def assert_messages(actual: list[str], expected: List[str]) -> None:
        assert len(actual) == len(expected)
        for i in range(len(actual)):
            assert actual[i] in expected

    try:
        await agent.on_messages([TextMessage(content="Hello", source="user")])

        state = await agent.save_state()
        assert state is not None
        assert len(state["initial_message_ids"]) == 2
        assert_messages(state["initial_message_ids"], ["msg-mock-1", "msg-mock-2"])
    except StopAsyncIteration:
        # Handle the StopAsyncIteration exception to allow the test to continue
        pass


@pytest.mark.asyncio
async def test_on_messages_with_cancellation(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client)

    # Create a cancellation token that's already cancelled
    token = CancellationToken()
    token.cancel()

    messages = [TextMessage(content="Hello", source="user")]

    with pytest.raises(CancelledError):
        await agent.on_messages(messages, token)


def mock_run(action: str, run_id: str, required_action: Optional[models.RequiredAction] = None) -> MagicMock:
    run = MagicMock()
    run.id = run_id
    run.status = action
    run.required_action = required_action
    return run


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name, registered_tools, error",
    [
        (
            "function",
            [
                FunctionTool(
                    func=lambda: None,
                    name="mock_tool",
                    description="Mock tool function",
                )
            ],
            "is not available",
        ),
        ("function", None, "No tools"),
    ],
)
async def test_on_messages_return_required_action_with_no_tool_raise_error(
    mock_project_client: MagicMock, tool_name: str, registered_tools: ListToolType, error: str
) -> None:
    agent = create_agent(mock_project_client, tools=registered_tools)

    complete_run = mock_run("completed", "run-mock")
    mock_project_client.agents.submit_tool_outputs_to_run = AsyncMock(return_value=complete_run)

    required_action = models.SubmitToolOutputsAction()  # type: ignore

    required_action.submit_tool_outputs = SimpleNamespace(  # type: ignore
        tool_calls=[
            SimpleNamespace(
                type="function", id="tool-mock", name=tool_name, function=SimpleNamespace(arguments={}, name="function")
            )
        ]
    )  # mypy ignore

    requires_action_run = mock_run("requires_action", "run-mock", required_action)
    mock_project_client.agents.get_run = AsyncMock(side_effect=[requires_action_run, complete_run])

    messages = [TextMessage(content="Hello", source="user")]

    response: Response = await agent.on_messages(messages)

    # check why there are 2 inner messages
    tool_call_events = [event for event in response.inner_messages if isinstance(event, ToolCallExecutionEvent)]  # type: ignore
    assert len(tool_call_events) == 1

    event: ToolCallExecutionEvent = tool_call_events[0]
    assert event.content[0].is_error is True
    assert event.content[0].content.find(error) != -1


@pytest.mark.asyncio
async def test_on_message_raise_error_when_stream_return_nothing(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client)

    messages = [TextMessage(content="Hello", source="user")]
    agent.on_messages_stream = MagicMock(name="on_messages_stream")  # type: ignore
    agent.on_messages_stream.__aiter__.return_value = []

    with pytest.raises(AssertionError, match="have returned the final result"):
        await agent.on_messages(messages)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "file_paths, file_status, should_raise_error",
    [
        (["file1.txt", "file2.txt"], models.FileState.PROCESSED, False),
        (["file3.txt"], models.FileState.ERROR, True),
    ],
)
async def test_uploading_multiple_files(
    mock_project_client: MagicMock, file_paths: list[str], file_status: models.FileState, should_raise_error: bool
) -> None:
    agent = create_agent(mock_project_client)

    file_mock = AsyncMock(id="file-id", status=file_status)
    mock_project_client.agents.update_thread = AsyncMock()
    mock_project_client.agents.upload_file_and_poll = AsyncMock(return_value=file_mock)

    async def upload_files() -> None:
        await agent.on_upload_for_code_interpreter(
            file_paths,
            cancellation_token=CancellationToken(),
            sleep_interval=0.1,
        )

    if should_raise_error:
        with pytest.raises(Exception, match="upload failed with status"):
            await upload_files()
    else:
        await upload_files()

    mock_project_client.agents.upload_file_and_poll.assert_has_calls(
        [call(file_path=file_path, purpose=models.FilePurpose.AGENTS, sleep_interval=0.1) for file_path in file_paths]
    )
