import json
import uuid
from unittest import mock

import pytest
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    DataPart,
    FilePart,
    FileWithBytes,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskNotFoundError,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    BaseAgentEvent,
    HandoffMessage,
    MultiModalMessage,
    StructuredMessage,
    TextMessage,
)
from autogen_core import CancellationToken, Image

from autogen_ext.agents.a2a._a2a_event_mapper import A2aEventMapper  # Assuming this is in the same directory
from autogen_ext.agents.a2a._a2a_hosted_agent import (
    A2aHostedAgent,
    A2aHostedAgentConfig,
    get_index_of_user_message,
)


async def async_return(value):
    return value


async def async_generator(values):
    for v in values:
        yield v


# --- Fixtures for common test setup ---


@pytest.fixture
def mock_agent_card():
    """A basic mock AgentCard for testing."""
    return AgentCard(
        name="test-agent",
        description="A descriptive test agent.",
        url="http://localhost:8080",
        capabilities=AgentCapabilities(streaming=True, image_generation=False, code_execution=False),
        skills=[],
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        supportsAuthenticatedExtendedCard=False,
    )


@pytest.fixture
def mock_a2a_event_mapper():
    """A mock A2aEventMapper."""
    mapper = mock.MagicMock(spec=A2aEventMapper)
    mapper.handle_message.side_effect = lambda msg: TextMessage(content=f"Agent says: {msg.parts[0].root.text}")
    mapper.handle_artifact.side_effect = lambda artifact: BaseAgentEvent(name="Artifact", data={"data": "test"})
    return mapper


@pytest.fixture
def basic_agent(mock_agent_card, mock_a2a_event_mapper):
    """Provides a basic A2aHostedAgent instance."""
    return A2aHostedAgent(
        agent_card=mock_agent_card,
        event_mapper=mock_a2a_event_mapper,
        http_kwargs={"timeout": 30},
        handoff_message="Custom handoff to {target}.",
    )


@pytest.fixture
def user_message_params():
    """Provides a sample MessageSendParams for a user message."""
    return MessageSendParams(
        message=Message(
            messageId=str(uuid.uuid4()),
            parts=[Part(root=TextPart(text="Hello agent!"))],
            role=Role.user,
            taskId="test-task-123",
        )
    )


# --- Test Cases for __init__ ---


class TestA2aHostedAgentInit:
    def test_default_initialization(self, mock_agent_card):
        agent = A2aHostedAgent(agent_card=mock_agent_card)
        assert agent._default_http_kwargs == {}
        assert agent._agent_card == mock_agent_card
        assert isinstance(agent._task_id, str) and len(agent._task_id) == 36  # UUID length
        assert isinstance(agent._event_mapper, A2aEventMapper)
        assert agent._event_mapper._agent_name == mock_agent_card.name
        assert agent._handoff_message == "Transferred to {target}, adopting the role of {target} immediately."

    def test_custom_initialization(self, mock_agent_card, mock_a2a_event_mapper):
        custom_http_kwargs = {"timeout": 60, "headers": {"Authorization": "Bearer abc"}}
        custom_handoff = "Take it, {target}!"
        agent = A2aHostedAgent(
            agent_card=mock_agent_card,
            event_mapper=mock_a2a_event_mapper,
            http_kwargs=custom_http_kwargs,
            handoff_message=custom_handoff,
        )
        assert agent._default_http_kwargs == custom_http_kwargs
        assert agent._agent_card == mock_agent_card
        assert agent._event_mapper == mock_a2a_event_mapper
        assert agent._handoff_message == custom_handoff


# --- Test Cases for Properties ---


class TestA2aHostedAgentProperties:
    def test_name_property(self, mock_agent_card):
        mock_agent_card.name = "My Test Agent 1.0"
        agent = A2aHostedAgent(agent_card=mock_agent_card)
        assert agent.name == "my-test-agent-1-0"  # slugified

    def test_description_property_no_skills(self, mock_agent_card):
        mock_agent_card.description = "A simple agent."
        mock_agent_card.skills = []
        agent = A2aHostedAgent(agent_card=mock_agent_card)
        assert agent.description == "A simple agent."

    def test_description_property_with_skills(self, mock_agent_card):
        mock_agent_card.description = "A versatile agent."
        mock_agent_card.skills = [
            AgentSkill(id="SkillA", name="SkillA", description="Does A", tags=[], examples=[]),
            AgentSkill(id="SkillB", name="SkillB", description="Does B", tags=[], examples=[]),
        ]
        agent = A2aHostedAgent(agent_card=mock_agent_card)
        expected_desc = "A versatile agent.\nSkills: \nSkillA - Does A\nSkillB - Does B"
        assert agent.description == expected_desc

    def test_produced_message_types_property(self, basic_agent):
        expected_types = (HandoffMessage, StructuredMessage, TextMessage, MultiModalMessage)
        assert basic_agent.produced_message_types == expected_types


# --- Test Cases for _build_a2a_message ---


class TestA2aHostedAgentBuildA2AMessage:
    def test_text_message_conversion(self, basic_agent):
        autogen_messages = [TextMessage(content="Hello from AutoGen!", source="user")]
        params = basic_agent._build_a2a_message(autogen_messages)
        assert params.message.role == Role.user
        assert len(params.message.parts) == 1
        part = params.message.parts[0].root
        assert isinstance(part, TextPart)
        assert part.text == "Hello from AutoGen!"

    def test_multi_modal_message_with_image(self, basic_agent):
        mock_image = mock.MagicMock(spec=Image)
        mock_image.to_base64.return_value = "base64encodedbytes"
        autogen_messages = [MultiModalMessage(content=[mock_image], source="user")]
        params = basic_agent._build_a2a_message(autogen_messages)
        assert len(params.message.parts) == 1
        part = params.message.parts[0].root
        assert isinstance(part, FilePart)
        assert part.file.bytes == "base64encodedbytes"

    def test_multi_modal_message_with_string(self, basic_agent):
        autogen_messages = [MultiModalMessage(content=["image description text"], source="user")]
        params = basic_agent._build_a2a_message(autogen_messages)
        assert len(params.message.parts) == 1
        part = params.message.parts[0].root
        assert isinstance(part, TextPart)
        assert part.text == "image description text"

    def test_structured_message_conversion(self, basic_agent):
        structured_content = {"tool_code": "print('hello')", "output_format": "json"}
        mock_model_message = mock.MagicMock()
        mock_model_message.content = json.dumps(structured_content)
        mock_structured_message = mock.MagicMock(spec=StructuredMessage)
        mock_structured_message.to_model_message.return_value = mock_model_message

        autogen_messages = [mock_structured_message]
        params = basic_agent._build_a2a_message(autogen_messages)
        assert len(params.message.parts) == 1
        part = params.message.parts[0].root
        assert isinstance(part, DataPart)
        assert part.data == structured_content


# --- Test Cases for _get_latest_handoff ---


class TestA2aHostedAgentGetLatestHandoff:
    def test_no_handoff_messages(self, basic_agent):
        messages = [TextMessage(content="Hi", source="user"), TextMessage(content="Hello", source="user2")]
        assert basic_agent._get_latest_handoff(messages) is None

    def test_handoff_message_for_current_agent(self, basic_agent):
        handoff_msg = HandoffMessage(content="Transfer", source="user", target=basic_agent.name)
        messages = [TextMessage(content="Hi", source="user"), handoff_msg]
        assert basic_agent._get_latest_handoff(messages) == handoff_msg

    def test_handoff_message_for_different_agent(self, basic_agent):
        handoff_msg = HandoffMessage(content="Transfer", source="user", target="another-agent")
        messages = [TextMessage(content="Hi", source="user"), handoff_msg]
        with pytest.raises(AssertionError, match="Handoff message target does not match agent name"):
            basic_agent._get_latest_handoff(messages)

    def test_multiple_handoff_messages_gets_latest(self, basic_agent):
        handoff_msg1 = HandoffMessage(content="Transfer1", source="user1", target=basic_agent.name)
        handoff_msg2 = HandoffMessage(content="Transfer2", source="user2", target=basic_agent.name)
        messages = [
            handoff_msg1,
            TextMessage(
                content="Mid",
                source="user1",
            ),
            handoff_msg2,
        ]
        assert basic_agent._get_latest_handoff(messages) == handoff_msg2


# --- Test Cases for on_messages ---


@pytest.mark.asyncio
class TestA2aHostedAgentOnMessages:
    async def test_successful_call_non_streaming(self, basic_agent, mocker):
        basic_agent._agent_card.capabilities.streaming = False
        mock_response_message = TextMessage(content="Agent's final response.", source="user")
        mock_call_agent_result = async_generator([mock_response_message])  # Yields mock_response_message
        mocker.patch.object(basic_agent, "call_agent", return_value=mock_call_agent_result)

        messages = [TextMessage(content="Start chat.", source="user")]
        cancellation_token = CancellationToken()
        response = await basic_agent.on_messages(messages, cancellation_token)

        basic_agent.call_agent.assert_called_once_with(mock.ANY, cancellation_token, mock.ANY)
        assert isinstance(response, Response)
        assert response.chat_message == mock_response_message
        assert response.inner_messages == []  # Only one message yielded

    async def test_successful_call_streaming(self, basic_agent, mocker):
        basic_agent._agent_card.capabilities.streaming = True
        mock_stream_messages = [
            TextMessage(content="Part 1", source=basic_agent.name),
            TextMessage(content="Part 2", source=basic_agent.name),
            TextMessage(content="Final message.", source=basic_agent.name),
        ]
        mock_call_agent_stream_result = async_generator(mock_stream_messages)
        mocker.patch.object(basic_agent, "call_agent_stream", return_value=mock_call_agent_stream_result)

        messages = [TextMessage(content="Stream chat.", source=basic_agent.name)]
        cancellation_token = CancellationToken()
        response = await basic_agent.on_messages(messages, cancellation_token)

        basic_agent.call_agent_stream.assert_called_once_with(mock.ANY, cancellation_token, mock.ANY)
        assert isinstance(response, Response)
        assert response.chat_message == mock_stream_messages[-1]
        assert response.inner_messages == mock_stream_messages[:-1]


# --- Test Cases for call_agent (Non-Streaming) ---


@pytest.mark.asyncio
class TestA2aHostedAgentCallAgent:
    async def test_successful_message_send_and_response(self, basic_agent, mocker, user_message_params):
        # Mock A2AClient and its methods
        mock_a2a_client = mocker.MagicMock()
        mocker.patch("autogen_ext.agents.a2a._a2a_hosted_agent.A2AClient", return_value=mock_a2a_client)

        # Mock the async context manager for httpx.AsyncClient
        mocker.patch("httpx.AsyncClient", autospec=True)
        httpx_client_instance = mocker.MagicMock()
        httpx_client_instance.__aenter__.return_value = httpx_client_instance
        httpx_client_instance.__aexit__.return_value = None
        mocker.patch("httpx.AsyncClient", return_value=httpx_client_instance)

        # Mock A2AClient.send_message response
        user_msg = Message(
            messageId=user_message_params.message.messageId,
            parts=[Part(root=TextPart(text="User input"))],
            role=Role.user,
            taskId="test-task-123",
        )
        agent_response_msg = Message(
            messageId=str(uuid.uuid4()),
            parts=[Part(root=TextPart(text="Agent's reply"))],
            role=Role.agent,
            taskId="test-task-123",
        )
        mock_a2a_client.send_message.return_value = async_return(
            SendMessageResponse(
                root=SendMessageSuccessResponse(
                    id="req_id",
                    result=Task(
                        contextId="contextId",
                        id="test-task-123",
                        history=[user_msg, agent_response_msg],
                        status=TaskStatus(state=TaskState.completed, message=None),
                    ),
                )
            )
        )

        cancellation_token = mocker.MagicMock(spec=CancellationToken)
        # Ensure _event_mapper.handle_message is properly mocked to return an Autogen message type
        basic_agent._event_mapper.handle_message.side_effect = lambda msg: TextMessage(
            content=msg.parts[0].root.text, source=basic_agent.name
        )

        response_generator = basic_agent.call_agent(user_message_params, cancellation_token)
        messages_yielded = [msg async for msg in response_generator]

        mock_a2a_client.send_message.assert_called_once()
        assert len(messages_yielded) == 1
        assert isinstance(messages_yielded[0], TextMessage)
        assert messages_yielded[0].content == "Agent's reply"
        cancellation_token.cancel.assert_not_called()

    async def test_a2a_client_returns_error_response(self, basic_agent, mocker, user_message_params):
        mock_a2a_client = mocker.MagicMock()
        mocker.patch("autogen_ext.agents.a2a._a2a_hosted_agent.A2AClient", return_value=mock_a2a_client)
        mocker.patch("httpx.AsyncClient", autospec=True)
        httpx_client_instance = mocker.MagicMock()
        httpx_client_instance.__aenter__.return_value = httpx_client_instance
        httpx_client_instance.__aexit__.return_value = None
        mocker.patch("httpx.AsyncClient", return_value=httpx_client_instance)

        mock_error = SendMessageResponse(root=JSONRPCErrorResponse(id="req_id", error=TaskNotFoundError()))
        mock_a2a_client.send_message.return_value = async_return(mock_error)

        cancellation_token = CancellationToken()
        response_generator = basic_agent.call_agent(user_message_params, cancellation_token)

        with pytest.raises(Exception, match="('Error in A2A response: Task not found', -32001, None)"):
            async for _ in response_generator:
                pass  # Consume the generator to trigger the exception

    async def test_task_state_canceled(self, basic_agent, mocker, user_message_params):
        mock_a2a_client = mocker.MagicMock()
        mocker.patch("autogen_ext.agents.a2a._a2a_hosted_agent.A2AClient", return_value=mock_a2a_client)
        mocker.patch("httpx.AsyncClient", autospec=True)
        httpx_client_instance = mocker.MagicMock()
        httpx_client_instance.__aenter__.return_value = httpx_client_instance
        httpx_client_instance.__aexit__.return_value = None
        mocker.patch("httpx.AsyncClient", return_value=httpx_client_instance)

        user_msg = Message(
            messageId=user_message_params.message.messageId,
            parts=[Part(root=TextPart(text="User input"))],
            role=Role.user,
            taskId="test-task-123",
        )
        agent_response_msg = Message(
            messageId=str(uuid.uuid4()),
            parts=[Part(root=TextPart(text="Task Canceled"))],
            role=Role.agent,
            taskId="test-task-123",
        )
        mock_a2a_client.send_message.return_value = async_return(
            SendMessageResponse(
                root=SendMessageSuccessResponse(
                    id="req_id",
                    result=Task(
                        id=str(uuid.uuid4()),
                        contextId=str(uuid.uuid4()),
                        history=[user_msg, agent_response_msg],
                        status=TaskStatus(state=TaskState.canceled),
                    ),
                )
            )
        )
        cancellation_token = mocker.MagicMock(spec=CancellationToken)

        # Ensure _event_mapper.handle_message is properly mocked to return an Autogen message type
        basic_agent._event_mapper.handle_message.side_effect = lambda msg: TextMessage(
            content=msg.parts[0].root.text, source="agent"
        )

        response_generator = basic_agent.call_agent(user_message_params, cancellation_token)
        messages_yielded = [msg async for msg in response_generator]

        cancellation_token.cancel.assert_called_once()
        assert len(messages_yielded) == 0


# --- Test Cases for on_reset, save_state, load_state ---


@pytest.mark.asyncio
class TestA2aHostedAgentStateManagement:
    async def test_on_reset_resets_task_id(self, basic_agent):
        old_task_id = basic_agent._task_id
        await basic_agent.on_reset(CancellationToken())
        assert basic_agent._task_id != old_task_id
        assert isinstance(basic_agent._task_id, str) and len(basic_agent._task_id) == 36

    async def test_save_state_returns_correct_state(self, basic_agent):
        saved_state = await basic_agent.save_state()
        assert saved_state == {"task_id": basic_agent._task_id}

    async def test_load_state_restores_correct_state(self, basic_agent):
        new_task_id = str(uuid.uuid4())
        await basic_agent.load_state({"task_id": new_task_id})
        assert basic_agent._task_id == new_task_id

    async def test_load_state_with_missing_task_id(self, basic_agent):
        original_task_id = basic_agent._task_id
        await basic_agent.load_state({"task_id": ""})  # Load empty state
        # load_state creates a new uuid if task_id is not in config
        assert basic_agent._task_id != original_task_id
        assert isinstance(basic_agent._task_id, str) and len(basic_agent._task_id) == 36


# --- Test Cases for get_index_of_user_message ---


class TestGetIndexOfUserMessage:
    def test_user_message_found(self, user_message_params):
        messages = [
            Message(messageId="1", role=Role.agent, parts=[]),
            user_message_params.message,
            Message(messageId="3", role=Role.agent, parts=[]),
        ]
        index = get_index_of_user_message(messages, user_message_params)
        assert index == 1

    def test_user_message_not_found(self, user_message_params):
        messages = [
            Message(messageId="1", role=Role.agent, parts=[]),
            Message(messageId="2", role=Role.user, parts=[]),  # Different messageId
            Message(messageId="3", role=Role.agent, parts=[]),
        ]
        with pytest.raises(AssertionError, match="User message not found in the messages list."):
            get_index_of_user_message(messages, user_message_params)

    def test_empty_message_list(self, user_message_params):
        messages = []
        with pytest.raises(AssertionError, match="User message not found in the messages list."):
            get_index_of_user_message(messages, user_message_params)
