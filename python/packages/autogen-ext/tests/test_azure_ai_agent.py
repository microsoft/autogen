import json
from asyncio import CancelledError
from types import SimpleNamespace
from typing import Any, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from autogen_agentchat.base._chat_agent import Response
from autogen_agentchat.messages import TextMessage, ToolCallExecutionEvent
from autogen_core._cancellation_token import CancellationToken
from autogen_core.tools._function_tool import FunctionTool
from autogen_ext.agents.azure._azure_ai_agent import AzureAIAgent
from autogen_ext.agents.azure._types import ListToolType
from azure.ai.agents.models import (
    AzureAISearchToolDefinition,
    AzureFunctionToolDefinition,
    BingGroundingToolDefinition,
    CodeInterpreterToolDefinition,
    FilePurpose,
    FileSearchToolDefinition,
    FileState,
    RequiredAction,
    RunStatus,
    SubmitToolOutputsAction,
    ThreadMessage,
)
from azure.ai.projects.aio import AIProjectClient


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

        :rtype: List[FakeTextContent]
        """
        if not self.content:
            return []
        return [content for content in self.content if isinstance(content, FakeTextContent)]


class FakeMessageUrlCitationDetails:
    def __init__(self, url: str, title: str) -> None:
        self.url = url
        self.title = title


class FakeTextUrlCitationAnnotation:
    def __init__(self, citation_details: FakeMessageUrlCitationDetails, text: str) -> None:
        self.type = "url_citation"
        self.url_citation = citation_details
        self.text = text


class FakeTextFileCitationDetails:
    def __init__(self, file_id: str, quote: str) -> None:
        self.file_id = file_id
        self.quote = quote


class FakeTextFileCitationAnnotation:
    def __init__(self, citation_details: FakeTextFileCitationDetails) -> None:
        self.type = "file_citation"
        self.file_citation = citation_details


class FakeMessageWithUrlCitationAnnotation:
    def __init__(self, id: str, text: str, annotations: list[FakeTextUrlCitationAnnotation]) -> None:
        self.id = id
        # The agent expects content to be a list of objects with a "type" attribute.
        self.content = [FakeTextContent(text)]
        self.role = "user"
        self._annotations = annotations

    @property
    def text_messages(self) -> List[FakeTextContent]:
        """Returns all text message contents in the messages.

        :rtype: List[FakeTextContent]
        """
        if not self.content:
            return []
        return [content for content in self.content if isinstance(content, FakeTextContent)]

    @property
    def url_citation_annotations(self) -> List[FakeTextUrlCitationAnnotation]:
        """Returns all URL citation annotations from text message annotations in the messages.

        :rtype: List[FakeTextUrlCitationAnnotation]
        """
        return self._annotations


class FakeMessageWithFileCitationAnnotation:
    def __init__(self, id: str, text: str, annotations: list[FakeTextFileCitationAnnotation]) -> None:
        self.id = id
        # The agent expects content to be a list of objects with a "type" attribute.
        self.content = [FakeTextContent(text)]
        self.role = "user"
        self._annotations = annotations

    @property
    def text_messages(self) -> List[FakeTextContent]:
        """Returns all text message contents in the messages.

        :rtype: List[FakeTextContent]
        """
        if not self.content:
            return []
        return [content for content in self.content if isinstance(content, FakeTextContent)]

    @property
    def file_citation_annotations(self) -> List[FakeTextFileCitationAnnotation]:
        """Returns all URL citation annotations from text message annotations in the messages.

        :rtype: List[FakeTextFileCitationAnnotation]
        """
        return self._annotations


class FakeMessageWithAnnotation:
    def __init__(self, id: str, text: str, annotations: list[FakeTextUrlCitationAnnotation]) -> None:
        self.id = id
        # The agent expects content to be a list of objects with a "type" attribute.
        self.content = [FakeTextContent(text)]
        self.role = "user"
        self.annotations = annotations

    @property
    def text_messages(self) -> List[FakeTextContent]:
        """Returns all text message contents in the messages.

        :rtype: List[FakeTextContent]
        """
        if not self.content:
            return []
        return [content for content in self.content if isinstance(content, FakeTextContent)]


FakeMessageType = Union[
    ThreadMessage
    | FakeMessage
    | FakeMessageWithAnnotation
    | FakeMessageWithUrlCitationAnnotation
    | FakeMessageWithFileCitationAnnotation
]


async def mock_messages_list(*args, **kwargs):
    """Mock async generator for messages.list()"""
    messages = [FakeMessage("msg-mock", "response")]
    for message in messages:
        yield message


async def mock_messages_list_empty(*args, **kwargs):
    """Mock async generator that yields no messages"""
    # This generator yields nothing, simulating an empty message list
    return
    yield  # This line is never reached but makes this a generator


async def mock_messages_list_multiple(*args, **kwargs):
    """Mock async generator for multiple messages (pagination test)"""
    messages = [
        FakeMessage("msg-mock-1", "response-1"),
        FakeMessage("msg-mock-2", "response-2"),
    ]
    for message in messages:
        yield message


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

    # Create separate operation groups to match the actual SDK structure
    client.agents = MagicMock()
    client.runs = MagicMock()
    client.messages = MagicMock()
    client.threads = MagicMock()
    client.files = MagicMock()
    client.vector_stores = MagicMock()
    client.vector_store_files = MagicMock()
    client.vector_store_file_batches = MagicMock()

    # Agent operations
    client.agents.create_agent = AsyncMock(return_value=MagicMock(id="assistant-mock"))
    client.agents.get_agent = AsyncMock(return_value=MagicMock(id="assistant-mock"))
    client.agents.update_agent = AsyncMock()
    client.agents.delete_agent = AsyncMock()

    agent_run = MagicMock()
    agent_run.id = "run-mock"
    agent_run.status = RunStatus.COMPLETED

    client.agents.runs = MagicMock()
    client.agents.runs.create = AsyncMock(return_value=agent_run)
    client.agents.runs.get = AsyncMock(return_value=agent_run)
    client.agents.runs.submit_tool_outputs = AsyncMock(return_value=agent_run)

    client.agents.messages = MagicMock()
    client.agents.messages.list = mock_messages_list
    client.agents.messages.create = AsyncMock()

    client.agents.threads = MagicMock()
    client.agents.threads.get = AsyncMock(return_value=MagicMock(id="thread-mock"))
    client.agents.threads.create = AsyncMock(return_value=MagicMock(id="thread-mock"))
    client.agents.threads.update = AsyncMock()

    client.agents.files = MagicMock()
    client.agents.files.upload_and_poll = AsyncMock(return_value=MagicMock(id="file-mock", status=FileState.PROCESSED))

    client.agents.vector_stores = MagicMock()
    client.agents.vector_stores.create_and_poll = AsyncMock(return_value=MagicMock(id="vector_store_id"))
    client.agents.vector_store_file_batches = MagicMock()
    client.agents.vector_store_file_batches.create_and_poll = AsyncMock()

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

    # The agent might call create_thread multiple times during initialization, so check if it was called at least once
    assert mock_project_client.agents.threads.create.call_count > 0


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
    file_mock = MagicMock()
    file_mock.id = "file-mock"
    file_mock.status = FileState.PROCESSED

    thread_mock = MagicMock()
    thread_mock.tool_resources = MagicMock()
    thread_mock.tool_resources.code_interpreter = MagicMock()
    thread_mock.tool_resources.code_interpreter.file_ids = []  # Set as a valid list

    mock_project_client.agents.files.upload_and_poll = AsyncMock(return_value=file_mock)
    mock_project_client.agents.threads.get = AsyncMock(return_value=thread_mock)
    mock_project_client.agents.threads.update = AsyncMock()

    agent = create_agent(
        mock_project_client,
    )

    file_paths = ["test_file_1.txt", "test_file_2.txt"]
    await agent.on_upload_for_code_interpreter(file_paths)

    mock_project_client.agents.files.upload_and_poll.assert_called()
    mock_project_client.agents.threads.get.assert_called_once()
    mock_project_client.agents.threads.update.assert_called_once()


@pytest.mark.asyncio
async def test_on_upload_for_file_search(mock_project_client: MagicMock) -> None:
    file_mock = MagicMock()
    file_mock.id = "file-mock"
    file_mock.status = FileState.PROCESSED  # Set a valid status

    mock_project_client.agents.files.upload_and_poll = AsyncMock(return_value=file_mock)
    mock_project_client.agents.vector_stores.create_and_poll = AsyncMock(return_value=MagicMock(id="vector_store_id"))
    mock_project_client.agents.update_agent = AsyncMock()
    mock_project_client.agents.vector_store_file_batches.create_and_poll = AsyncMock()

    agent = create_agent(mock_project_client, tools=["file_search"])

    file_paths = ["test_file_1.txt", "test_file_2.txt"]
    await agent.on_upload_for_file_search(file_paths, cancellation_token=CancellationToken())

    mock_project_client.agents.files.upload_and_poll.assert_called()
    mock_project_client.agents.vector_stores.create_and_poll.assert_called_once()
    mock_project_client.agents.update_agent.assert_called_once()
    mock_project_client.agents.vector_store_file_batches.create_and_poll.assert_called_once()


@pytest.mark.asyncio
async def test_upload_files(mock_project_client: MagicMock) -> None:
    mock_project_client.agents.vector_store_file_batches.create_and_poll = AsyncMock()

    mock_project_client.agents.update_agent = AsyncMock()
    mock_project_client.agents.vector_stores.create_and_poll = AsyncMock(return_value=MagicMock(id="vector_store_id"))

    mock_project_client.agents.files.upload_and_poll = AsyncMock(
        return_value=MagicMock(id="file-id", status=FileState.PROCESSED)
    )

    agent = create_agent(mock_project_client, tools=["file_search"])

    await agent.on_upload_for_file_search(["test_file.txt"], cancellation_token=CancellationToken())

    mock_project_client.agents.files.upload_and_poll.assert_any_await(
        file_path="test_file.txt", purpose=FilePurpose.AGENTS, polling_interval=0.5
    )


@pytest.mark.asyncio
async def test_on_messages_stream(mock_project_client: MagicMock) -> None:
    mock_project_client.agents.runs.create = AsyncMock(  # Corrected path
        return_value=MagicMock(id="run-id", status=RunStatus.COMPLETED)
    )
    mock_project_client.agents.messages.list = mock_messages_list  # Corrected path

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
        # ("sharepoint_grounding", False),
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
        agent = create_agent(mock_project_client, tools=[tool_name])
        assert agent.tools[0].type == tool_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_definition",
    [
        FileSearchToolDefinition(),
        CodeInterpreterToolDefinition(),
        BingGroundingToolDefinition(),  # type: ignore
        AzureFunctionToolDefinition(),  # type: ignore
        AzureAISearchToolDefinition(),
        # SharepointToolDefinition(),  # type: ignore
    ],
)
async def test_adding_tools_as_typed_definition(mock_project_client: MagicMock, tool_definition: Any) -> None:
    agent = create_agent(mock_project_client, tools=[tool_definition])

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

    mock_project_client.agents.threads.create.assert_awaited_once()  # Corrected path


@pytest.mark.asyncio
async def test_agent_initialization_with_thread_id(mock_project_client: MagicMock) -> None:
    agent = create_agent(mock_project_client, thread_id="thread-mock")

    await agent.on_messages([TextMessage(content="Hello", source="user")])

    mock_project_client.agents.threads.get.assert_awaited_once()  # Corrected path


@pytest.mark.asyncio
async def test_agent_initialization_fetching_multiple_pages_of_thread_messages(mock_project_client: MagicMock) -> None:
    mock_project_client.agents.threads.get = AsyncMock(return_value=MagicMock(id="thread-id"))  # Corrected path
    # Mock the list_messages method to return multiple messages
    mock_project_client.agents.messages.list = mock_messages_list_multiple  # Corrected path

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


def mock_run(action: str, run_id: str, required_action: Optional[RequiredAction] = None) -> MagicMock:
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

    complete_run = mock_run(RunStatus.COMPLETED, "run-mock")
    mock_project_client.agents.runs.submit_tool_outputs = AsyncMock(return_value=complete_run)  # Corrected path

    required_action = SubmitToolOutputsAction(
        submit_tool_outputs=SimpleNamespace(  # type: ignore
            tool_calls=[
                SimpleNamespace(
                    type="function",
                    id="tool-mock",
                    name=tool_name,
                    function=SimpleNamespace(arguments={}, name="function"),
                )
            ]
        )
    )

    required_action.submit_tool_outputs = SimpleNamespace(  # type: ignore
        tool_calls=[
            SimpleNamespace(
                type="function", id="tool-mock", name=tool_name, function=SimpleNamespace(arguments={}, name="function")
            )
        ]
    )  # mypy ignore

    requires_action_run = mock_run(RunStatus.REQUIRES_ACTION, "run-mock", required_action)
    mock_project_client.agents.runs.get = AsyncMock(side_effect=[requires_action_run, complete_run])  # Corrected path

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
        (["file1.txt", "file2.txt"], FileState.PROCESSED, False),
        (["file3.txt"], FileState.ERROR, True),
    ],
)
async def test_uploading_multiple_files(
    mock_project_client: MagicMock, file_paths: list[str], file_status: FileState, should_raise_error: bool
) -> None:
    agent = create_agent(mock_project_client)

    file_mock = MagicMock(id="file-id", status=file_status)
    mock_project_client.agents.threads.update = AsyncMock()
    mock_project_client.agents.files.upload_and_poll = AsyncMock(return_value=file_mock)

    async def upload_files() -> None:
        await agent.on_upload_for_code_interpreter(
            file_paths,
            cancellation_token=CancellationToken(),
            polling_interval=0.1,
        )

    if should_raise_error:
        with pytest.raises(ValueError, match="upload failed with status"):  # Changed from Exception to ValueError
            await upload_files()
    else:
        await upload_files()

    mock_project_client.agents.files.upload_and_poll.assert_has_calls(
        [call(file_path=file_path, purpose=FilePurpose.AGENTS, polling_interval=0.1) for file_path in file_paths]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fake_message, url, title",
    [
        (
            FakeMessageWithAnnotation(
                "msg-mock-1",
                "response-1",
                [FakeTextUrlCitationAnnotation(FakeMessageUrlCitationDetails("url1", "title1"), "text")],
            ),
            "url1",
            "title1",
        ),
        (
            FakeMessageWithUrlCitationAnnotation(
                "msg-mock-2",
                "response-2",
                [FakeTextUrlCitationAnnotation(FakeMessageUrlCitationDetails("url2", "title2"), "text")],
            ),
            "url2",
            "title2",
        ),
    ],
)
async def test_on_message_stream_mapping_url_citation(
    mock_project_client: MagicMock,
    fake_message: FakeMessageWithAnnotation | FakeMessageWithUrlCitationAnnotation,
    url: str,
    title: str,
) -> None:
    mock_project_client.agents.runs.create = AsyncMock(  # Corrected path and method name
        return_value=MagicMock(id="run-id", status=RunStatus.COMPLETED)
    )

    async def mock_messages_list_with_citation(*args, **kwargs):
        """Mock async generator for messages with citation"""
        yield fake_message

    mock_project_client.agents.messages.list = mock_messages_list_with_citation

    agent = create_agent(mock_project_client)

    messages = [TextMessage(content="Hello", source="user")]

    async for response in agent.on_messages_stream(messages):
        assert isinstance(response, Response)
        assert response.chat_message is not None
        assert response.chat_message.metadata is not None

        citations = json.loads(response.chat_message.metadata["citations"])
        assert citations is not None

        assert len(citations) == 1

        assert citations[0]["url"] == url
        assert citations[0]["title"] == title


@pytest.mark.asyncio
async def test_on_message_stream_mapping_file_citation(mock_project_client: MagicMock) -> None:
    mock_project_client.agents.create_run = AsyncMock(return_value=MagicMock(id="run-id", status=RunStatus.COMPLETED))

    expected_file_id = "file_id_1"
    expected_quote = "this part of a file"

    fake_message = FakeMessageWithFileCitationAnnotation(
        "msg-mock-1",
        "response-1",
        [FakeTextFileCitationAnnotation(FakeTextFileCitationDetails(expected_file_id, expected_quote))],
    )

    async def mock_messages_list_with_file_citation(*args, **kwargs):
        """Mock async generator for messages with file citation"""
        yield fake_message

    mock_project_client.agents.messages.list = mock_messages_list_with_file_citation

    agent = create_agent(mock_project_client)

    messages = [TextMessage(content="Hello", source="user")]

    async for response in agent.on_messages_stream(messages):
        assert isinstance(response, Response)
        assert response.chat_message is not None
        assert response.chat_message.metadata is not None

        citations = json.loads(response.chat_message.metadata["citations"])
        assert citations is not None

        assert len(citations) == 1

        assert citations[0]["file_id"] == expected_file_id
        assert citations[0]["text"] == expected_quote
