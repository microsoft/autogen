import io
import os
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Union
from unittest.mock import AsyncMock, MagicMock

import aiofiles
import pytest
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_core import CancellationToken
from autogen_core.tools._base import BaseTool, Tool
from autogen_ext.agents.openai import OpenAIAssistantAgent
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI
from pydantic import BaseModel


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    FREE_RESPONSE = "FREE_RESPONSE"


class Question(BaseModel):
    question_text: str
    question_type: QuestionType
    choices: Optional[List[str]] = None


class DisplayQuizArgs(BaseModel):
    title: str
    questions: List[Question]


class QuizResponses(BaseModel):
    responses: List[str]


class DisplayQuizTool(BaseTool[DisplayQuizArgs, QuizResponses]):
    def __init__(self) -> None:
        super().__init__(
            args_type=DisplayQuizArgs,
            return_type=QuizResponses,
            name="display_quiz",
            description=(
                "Displays a quiz to the student and returns the student's responses. "
                "A single quiz can have multiple questions."
            ),
        )

    async def run(self, args: DisplayQuizArgs, cancellation_token: CancellationToken) -> QuizResponses:
        responses: List[str] = []
        for q in args.questions:
            if q.question_type == QuestionType.MULTIPLE_CHOICE:
                response = q.choices[0] if q.choices else ""
            elif q.question_type == QuestionType.FREE_RESPONSE:
                response = "Sample free response"
            else:
                response = ""
            responses.append(response)
        return QuizResponses(responses=responses)


class FakeText:
    def __init__(self, value: str):
        self.value = value


class FakeTextContent:
    def __init__(self, text: str):
        self.type = "text"
        self.text = FakeText(text)


class FakeMessage:
    def __init__(self, id: str, text: str):
        self.id = id
        # The agent expects content to be a list of objects with a "type" attribute.
        self.content = [FakeTextContent(text)]


class FakeCursorPage:
    def __init__(self, data: List[ChatMessage | FakeMessage]) -> None:
        self.data = data

    def has_next_page(self) -> bool:
        return False


def create_mock_openai_client() -> AsyncAzureOpenAI:
    # Create the base client as an AsyncMock.
    client = AsyncMock(spec=AsyncAzureOpenAI)

    # Create a "beta" attribute with the required nested structure.
    beta = MagicMock()
    client.beta = beta

    # Setup beta.assistants with dummy create/retrieve/update/delete.
    beta.assistants = MagicMock()
    beta.assistants.create = AsyncMock(return_value=MagicMock(id="assistant-mock"))
    beta.assistants.retrieve = AsyncMock(return_value=MagicMock(id="assistant-mock"))
    beta.assistants.update = AsyncMock(return_value=MagicMock(id="assistant-mock"))
    beta.assistants.delete = AsyncMock(return_value=None)

    # Setup beta.threads with create and retrieve.
    beta.threads = MagicMock()
    beta.threads.create = AsyncMock(return_value=MagicMock(id="thread-mock", tool_resources=None))
    beta.threads.retrieve = AsyncMock(return_value=MagicMock(id="thread-mock", tool_resources=None))

    # Setup beta.threads.messages with create, list, and delete.
    beta.threads.messages = MagicMock()
    beta.threads.messages.create = AsyncMock(return_value=MagicMock(id="msg-mock", content="mock content"))

    # Default fake messages – these may be overridden in individual tests.
    name_message = FakeMessage("msg-mock", "Your name is John, you are a software engineer.")

    def mock_list(thread_id: str, **kwargs: Dict[str, Any]) -> FakeCursorPage:
        # Default behavior returns the "name" message.
        if thread_id == "thread-mock":
            return FakeCursorPage([name_message])
        return FakeCursorPage([FakeMessage("msg-mock", "Default response")])

    beta.threads.messages.list = AsyncMock(side_effect=mock_list)
    beta.threads.messages.delete = AsyncMock(return_value=MagicMock(deleted=True))

    # Setup beta.threads.runs with create, retrieve, and submit_tool_outputs.
    beta.threads.runs = MagicMock()
    beta.threads.runs.create = AsyncMock(return_value=MagicMock(id="run-mock", status="completed"))
    beta.threads.runs.retrieve = AsyncMock(return_value=MagicMock(id="run-mock", status="completed"))
    beta.threads.runs.submit_tool_outputs = AsyncMock(return_value=MagicMock(id="run-mock", status="completed"))

    # Setup beta.vector_stores with create, delete, and file_batches.
    beta.vector_stores = MagicMock()
    beta.vector_stores.create = AsyncMock(return_value=MagicMock(id="vector-mock"))
    beta.vector_stores.delete = AsyncMock(return_value=None)
    beta.vector_stores.file_batches = MagicMock()
    beta.vector_stores.file_batches.create_and_poll = AsyncMock(return_value=None)

    # Setup client.files with create and delete.
    client.files = MagicMock()
    client.files.create = AsyncMock(return_value=MagicMock(id="file-mock"))
    client.files.delete = AsyncMock(return_value=None)

    return client


# Fixture for the mock client.
@pytest.fixture
def mock_openai_client() -> AsyncAzureOpenAI:
    return create_mock_openai_client()


@pytest.fixture
def client() -> AsyncAzureOpenAI:
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    # Return mock client if credentials not available
    if not azure_endpoint or not api_key:
        return create_mock_openai_client()

    # Try Azure CLI credentials if API key not provided
    if not api_key:
        try:
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            return AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint, api_version=api_version, azure_ad_token_provider=token_provider
            )
        except Exception:
            return create_mock_openai_client()

    # Fall back to API key auth if provided
    return AsyncAzureOpenAI(azure_endpoint=azure_endpoint, api_version=api_version, api_key=api_key)


@pytest.fixture
def agent(client: AsyncAzureOpenAI) -> OpenAIAssistantAgent:
    tools: List[Union[Literal["code_interpreter", "file_search"], Tool]] = [
        "code_interpreter",
        "file_search",
        DisplayQuizTool(),
    ]

    return OpenAIAssistantAgent(
        name="assistant",
        instructions="Help the user with their task.",
        model="gpt-4o-mini",
        description="OpenAI Assistant Agent",
        client=client,
        tools=tools,
    )


@pytest.fixture
def cancellation_token() -> CancellationToken:
    return CancellationToken()


# A fake aiofiles.open to bypass filesystem access.
@asynccontextmanager
async def fake_aiofiles_open(*args: Any, **kwargs: Dict[str, Any]) -> AsyncGenerator[io.BytesIO, None]:
    yield io.BytesIO(b"dummy file content")


@pytest.mark.asyncio
async def test_file_retrieval(
    agent: OpenAIAssistantAgent, cancellation_token: CancellationToken, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange: Define a fake async file opener that returns a file-like object with an async read() method.
    class FakeAiofilesFile:
        async def read(self) -> bytes:
            return b"dummy file content"

    @asynccontextmanager
    async def fake_async_aiofiles_open(*args: Any, **kwargs: Dict[str, Any]) -> AsyncGenerator[FakeAiofilesFile, None]:
        yield FakeAiofilesFile()

    monkeypatch.setattr(aiofiles, "open", fake_async_aiofiles_open)

    # We also override the messages.list to return a fake file search result.
    fake_file_message = FakeMessage(
        "msg-mock", "The first sentence of the jungle book is 'Mowgli was raised by wolves.'"
    )
    agent._client.beta.threads.messages.list = AsyncMock(return_value=FakeCursorPage([fake_file_message]))  # type: ignore

    # Create a temporary file.
    file_path = tmp_path / "jungle_book.txt"
    file_path.write_text("dummy content")

    await agent.on_upload_for_file_search(str(file_path), cancellation_token)

    message = TextMessage(source="user", content="What is the first sentence of the jungle scout book?")
    response = await agent.on_messages([message], cancellation_token)

    assert response.chat_message.content is not None
    assert isinstance(response.chat_message.content, str)
    assert len(response.chat_message.content) > 0

    await agent.delete_uploaded_files(cancellation_token)
    await agent.delete_vector_store(cancellation_token)
    await agent.delete_assistant(cancellation_token)


@pytest.mark.asyncio
async def test_code_interpreter(
    agent: OpenAIAssistantAgent, cancellation_token: CancellationToken, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: For code interpreter, have the messages.list return a result with "x = 1".
    agent._client.beta.threads.messages.list = AsyncMock(  # type: ignore
        return_value=FakeCursorPage([FakeMessage("msg-mock", "x = 1")])
    )

    message = TextMessage(source="user", content="I need to solve the equation `3x + 11 = 14`. Can you help me?")
    response = await agent.on_messages([message], cancellation_token)

    assert response.chat_message.content is not None
    assert isinstance(response.chat_message.content, str)
    assert len(response.chat_message.content) > 0
    assert "x = 1" in response.chat_message.content.lower()

    await agent.delete_assistant(cancellation_token)


@pytest.mark.asyncio
async def test_quiz_creation(
    agent: OpenAIAssistantAgent, cancellation_token: CancellationToken, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DisplayQuizTool, "run_json", DisplayQuizTool.run)

    # Create a fake tool call for display_quiz.
    fake_tool_call = MagicMock()
    fake_tool_call.type = "function"
    fake_tool_call.id = "tool-call-1"
    fake_tool_call.function = MagicMock()
    fake_tool_call.function.name = "display_quiz"
    fake_tool_call.function.arguments = (
        '{"title": "Quiz Title", "questions": [{"question_text": "What is 2+2?", '
        '"question_type": "MULTIPLE_CHOICE", "choices": ["3", "4", "5"]}]}'
    )

    # Create a run that requires action (tool call).
    run_requires_action = MagicMock()
    run_requires_action.id = "run-mock"
    run_requires_action.status = "requires_action"
    run_requires_action.required_action = MagicMock()
    run_requires_action.required_action.submit_tool_outputs = MagicMock()
    run_requires_action.required_action.submit_tool_outputs.tool_calls = [fake_tool_call]

    # Create a completed run for the subsequent retrieval.
    run_completed = MagicMock()
    run_completed.id = "run-mock"
    run_completed.status = "completed"
    run_completed.required_action = None

    # Set up the beta.threads.runs.retrieve mock to return these in sequence.
    agent._client.beta.threads.runs.retrieve.side_effect = [run_requires_action, run_completed]  # type: ignore

    # Also, set the messages.list call (after run completion) to return a quiz message.
    quiz_tool_message = FakeMessage("msg-mock", "Quiz created: Q1) 2+2=? Answer: b) 4; Q2) Free: Sample free response")
    agent._client.beta.threads.messages.list = AsyncMock(return_value=FakeCursorPage([quiz_tool_message]))  # type: ignore

    # Create a user message to trigger the tool invocation.
    message = TextMessage(
        source="user",
        content="Create a short quiz about basic math with one multiple choice question and one free response question.",
    )
    response = await agent.on_messages([message], cancellation_token)

    # Check that the final response has non-empty inner messages (i.e. tool call events).
    assert response.chat_message.content is not None
    assert isinstance(response.chat_message.content, str)
    assert len(response.chat_message.content) > 0
    assert isinstance(response.inner_messages, list)
    # Ensure that at least one inner message has non-empty content.
    assert any(hasattr(tool_msg, "content") and tool_msg.content for tool_msg in response.inner_messages)

    await agent.delete_assistant(cancellation_token)


@pytest.mark.asyncio
async def test_on_reset_behavior(client: AsyncAzureOpenAI, cancellation_token: CancellationToken) -> None:
    # Arrange: Use the default behavior for reset.
    thread = await client.beta.threads.create()
    await client.beta.threads.messages.create(
        thread_id=thread.id,
        content="Hi, my name is John and I'm a software engineer. Use this information to help me.",
        role="user",
    )

    agent = OpenAIAssistantAgent(
        name="assistant",
        instructions="Help the user with their task.",
        model="gpt-4o-mini",
        description="OpenAI Assistant Agent",
        client=client,
        thread_id=thread.id,
    )

    message1 = TextMessage(source="user", content="What is my name?")
    response1 = await agent.on_messages([message1], cancellation_token)
    assert isinstance(response1.chat_message.content, str)
    assert "john" in response1.chat_message.content.lower()

    await agent.on_reset(cancellation_token)

    message2 = TextMessage(source="user", content="What is my name?")
    response2 = await agent.on_messages([message2], cancellation_token)
    assert isinstance(response2.chat_message.content, str)
    assert "john" in response2.chat_message.content.lower()

    await agent.delete_assistant(cancellation_token)


@pytest.mark.asyncio
async def test_save_and_load_state(mock_openai_client: AsyncAzureOpenAI) -> None:
    agent = OpenAIAssistantAgent(
        name="assistant",
        description="Dummy assistant for state testing",
        client=mock_openai_client,
        model="dummy-model",
        instructions="dummy instructions",
        tools=[],
    )
    agent._assistant_id = "assistant-123"  # type: ignore
    agent._init_thread_id = "thread-456"  # type: ignore
    agent._initial_message_ids = {"msg1", "msg2"}  # type: ignore
    agent._vector_store_id = "vector-789"  # type: ignore
    agent._uploaded_file_ids = ["file-abc", "file-def"]  # type: ignore

    saved_state = await agent.save_state()

    new_agent = OpenAIAssistantAgent(
        name="assistant",
        description="Dummy assistant for state testing",
        client=mock_openai_client,
        model="dummy-model",
        instructions="dummy instructions",
        tools=[],
    )
    await new_agent.load_state(saved_state)

    assert new_agent._assistant_id == "assistant-123"  # type: ignore
    assert new_agent._init_thread_id == "thread-456"  # type: ignore
    assert new_agent._initial_message_ids == {"msg1", "msg2"}  # type: ignore
    assert new_agent._vector_store_id == "vector-789"  # type: ignore
    assert new_agent._uploaded_file_ids == ["file-abc", "file-def"]  # type: ignore
