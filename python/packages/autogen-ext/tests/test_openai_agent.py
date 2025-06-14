import json
from typing import Any, AsyncGenerator, Dict, List, Mapping, Optional, Type, Union, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, MultiModalMessage, TextMessage
from autogen_core import CancellationToken, FunctionCall, Image
from autogen_core.models import UserMessage
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.agents.openai import OpenAIAgent
from openai import AsyncOpenAI
from pydantic import BaseModel


class FakeChunkDelta:
    def __init__(self, content: Optional[str] = None, tool_calls: Optional[List[Any]] = None) -> None:
        self.content = content
        self.tool_calls = tool_calls


class FakeChunkChoice:
    def __init__(self, delta: Optional[FakeChunkDelta] = None, finish_reason: Optional[str] = None) -> None:
        self.delta = delta
        self.finish_reason = finish_reason
        self.index = 0


class FakeChunk:
    def __init__(self, id: str = "chunk-1", choices: Optional[List[FakeChunkChoice]] = None) -> None:
        self.id = id
        self.choices = choices or []


class FakeToolCallFunction:
    def __init__(self, name: str = "", arguments: str = "") -> None:
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, id: str = "call-1", function: Optional[FakeToolCallFunction] = None) -> None:
        self.id = id
        self.type = "function"
        self.function = function or FakeToolCallFunction()


def create_mock_openai_client() -> AsyncOpenAI:
    """Create a mock OpenAI client for the Responses API."""
    client = AsyncMock(spec=AsyncOpenAI)

    async def mock_responses_create(**kwargs: Any) -> Any:
        class MockResponse:
            def __init__(self, output_text: str, id: str) -> None:
                self.output_text = output_text
                self.id = id

        if "tools" in kwargs and kwargs["tools"]:
            return MockResponse(output_text='{"temperature": 72.5, "conditions": "sunny"}', id="resp-123")
        return MockResponse(output_text="Hello world!", id="resp-abc")

    responses = MagicMock()
    responses.create = AsyncMock(side_effect=mock_responses_create)
    client.responses = responses
    return client


@pytest.fixture
def mock_openai_client() -> AsyncOpenAI:
    return create_mock_openai_client()


@pytest.fixture
def mock_error_client() -> AsyncOpenAI:
    client = AsyncMock(spec=AsyncOpenAI)
    beta = MagicMock()
    client.beta = beta
    beta.chat = MagicMock()
    beta.chat.completions = MagicMock()

    async def mock_create_error(**kwargs: Any) -> None:
        raise Exception("API Error")

    responses = MagicMock()
    responses.create = AsyncMock(side_effect=mock_create_error)
    client.responses = responses
    return client


@pytest.fixture
def cancellation_token() -> CancellationToken:
    return CancellationToken()


class WeatherResponse(BaseModel):
    temperature: float
    conditions: str


class GetWeatherArgs(BaseModel):
    location: str


class WeatherTool(Tool):
    def __init__(self) -> None:
        self._name = "get_weather"
        self._description = "Get the current weather in a location"
        self._input_schema = GetWeatherArgs
        self._output_schema = WeatherResponse
        self._schema = ToolSchema(
            name=self._name,
            description=self._description,
            parameters={
                "type": "object",
                "properties": {"location": {"type": "string", "description": "The location to get weather for"}},
                "required": ["location"],
            },
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Get the current weather in a location"

    @property
    def schema(self) -> ToolSchema:
        return self._schema

    def args_type(self) -> Type[BaseModel]:
        return GetWeatherArgs

    def return_type(self) -> Type[Any]:
        return WeatherResponse

    def state_type(self) -> Type[BaseModel] | None:
        return None

    def return_value_as_string(self, value: Any) -> str:
        if isinstance(value, dict):
            return json.dumps(value)
        return str(value)

    async def run_json(
        self, args: Mapping[str, Any], cancellation_token: CancellationToken, call_id: str | None = None
    ) -> Dict[str, Any]:
        _ = GetWeatherArgs(**args)
        return WeatherResponse(temperature=72.5, conditions="sunny").model_dump()

    async def load_state_json(self, state: Mapping[str, Any]) -> None:
        pass

    async def save_state_json(self) -> Mapping[str, Any]:
        return {}


@pytest.fixture
def weather_tool() -> WeatherTool:
    return WeatherTool()


@pytest.fixture
def failing_tool() -> Tool:
    tool = MagicMock(spec=Tool)
    tool.name = "failing_tool"
    tool.run_json = AsyncMock(side_effect=Exception("Tool execution failed"))
    return tool


@pytest.fixture
def agent(mock_openai_client: AsyncOpenAI, weather_tool: WeatherTool) -> OpenAIAgent:
    return OpenAIAgent(
        name="assistant",
        description="Test assistant using the Response API",
        client=mock_openai_client,
        model="gpt-4o",
        instructions="You are a helpful AI assistant.",
        tools=[weather_tool],
        temperature=0.7,
        max_output_tokens=1000,
        store=True,
        truncation="auto",
    )


@pytest.fixture
def json_mode_agent(mock_openai_client: AsyncOpenAI) -> OpenAIAgent:
    return OpenAIAgent(
        name="json_assistant",
        description="JSON assistant",
        client=mock_openai_client,
        model="gpt-4o",
        instructions="Return JSON responses",
        json_mode=True,
    )


@pytest.fixture
def error_agent(mock_error_client: AsyncOpenAI) -> OpenAIAgent:
    return OpenAIAgent(
        name="error_assistant",
        description="Assistant that generates errors",
        client=mock_error_client,
        model="gpt-4o",
        instructions="You are a helpful AI assistant.",
    )


@pytest.mark.asyncio
async def test_basic_response(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    """Test that the agent returns a basic text response from the Responses API."""
    message = TextMessage(source="user", content="Hello, how are you?")
    response = await agent.on_messages([message], cancellation_token)

    assert response.chat_message is not None
    assert isinstance(response.chat_message, TextMessage)
    assert response.chat_message.content in ("Hello world!", '{"temperature": 72.5, "conditions": "sunny"}')
    assert response.chat_message.source == "assistant"


@pytest.mark.asyncio
async def test_tool_calling(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    """Test that the agent can call a tool and return the result using the Responses API."""

    async def mock_run_json(self: Any, args: Dict[str, Any], cancellation_token: CancellationToken) -> Dict[str, Any]:
        return {"temperature": 75.0, "conditions": "sunny and clear"}

    with patch.object(WeatherTool, "run_json", mock_run_json):
        message = TextMessage(source="user", content="What's the weather in New York?")

        all_messages: List[Any] = []
        async for msg in agent.on_messages_stream([message], cancellation_token):
            all_messages.append(msg)

        final_response = next((msg for msg in all_messages if hasattr(msg, "chat_message")), None)
        assert final_response is not None
        assert hasattr(final_response, "chat_message")
        response_msg = cast(Response, final_response)
        assert isinstance(response_msg.chat_message, TextMessage)
        assert response_msg.chat_message.content in (
            '{"temperature": 75.0, "conditions": "sunny and clear"}',
            '{"temperature": 72.5, "conditions": "sunny"}',
        )


@pytest.mark.asyncio
async def test_error_handling(error_agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    """Test that the agent returns an error message if the Responses API fails."""
    message = TextMessage(source="user", content="This will cause an error")

    all_messages: List[Any] = []
    async for msg in error_agent.on_messages_stream([message], cancellation_token):
        all_messages.append(msg)

    final_response = next((msg for msg in all_messages if hasattr(msg, "chat_message")), None)
    assert final_response is not None
    assert isinstance(final_response.chat_message, TextMessage)
    assert "Error generating response:" in final_response.chat_message.content


@pytest.mark.asyncio
async def test_state_management(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    agent._last_response_id = "resp-123"  # type: ignore
    agent._message_history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there"}]  # type: ignore

    state = await agent.save_state()

    new_agent = OpenAIAgent(
        name="assistant2",
        description="Test assistant 2",
        client=agent._client,  # type: ignore
        model="gpt-4o",
        instructions="You are a helpful AI assistant.",
    )

    await new_agent.load_state(state)

    assert new_agent._last_response_id == "resp-123"  # type: ignore
    assert len(new_agent._message_history) == 2  # type: ignore
    assert new_agent._message_history[0]["role"] == "user"  # type: ignore
    assert new_agent._message_history[0]["content"] == "Hello"  # type: ignore

    await new_agent.on_reset(cancellation_token)
    assert new_agent._last_response_id is None  # type: ignore
    assert len(new_agent._message_history) == 0  # type: ignore


@pytest.mark.asyncio
async def test_convert_message_functions(agent: OpenAIAgent) -> None:
    from autogen_ext.agents.openai._openai_agent import _convert_message_to_openai_message  # type: ignore

    user_msg = TextMessage(content="Hello", source="user")
    openai_user_msg = _convert_message_to_openai_message(user_msg)  # type: ignore
    assert openai_user_msg["role"] == "user"
    assert openai_user_msg["content"] == "Hello"

    sys_msg = TextMessage(content="System prompt", source="system")
    openai_sys_msg = _convert_message_to_openai_message(sys_msg)  # type: ignore
    assert openai_sys_msg["role"] == "system"
    assert openai_sys_msg["content"] == "System prompt"

    assistant_msg = TextMessage(content="Assistant reply", source="assistant")
    openai_assistant_msg = _convert_message_to_openai_message(assistant_msg)  # type: ignore
    assert openai_assistant_msg["role"] == "assistant"
    assert openai_assistant_msg["content"] == "Assistant reply"

    text_msg = TextMessage(content="Plain text", source="other")
    openai_text_msg = _convert_message_to_openai_message(text_msg)  # type: ignore
    assert openai_text_msg["role"] == "user"
    assert openai_text_msg["content"] == "Plain text"


@pytest.mark.asyncio
async def test_tool_schema_conversion(agent: OpenAIAgent) -> None:
    from autogen_ext.agents.openai._openai_agent import _convert_tool_to_function_schema  # type: ignore

    tool_schema = _convert_tool_to_function_schema(agent._tool_map["get_weather"])  # type: ignore

    assert tool_schema["name"] == "get_weather"
    assert "description" in tool_schema
    assert "parameters" in tool_schema
    assert tool_schema["parameters"]["type"] == "object"
    assert "properties" in tool_schema["parameters"]


@pytest.mark.asyncio
async def test_list_assistants(agent: OpenAIAgent) -> Dict[str, Any]:
    client = cast(Any, agent._client)  # type: ignore
    client.assistants = MagicMock()
    client.assistants.list = AsyncMock(
        return_value=MagicMock(model_dump=lambda: {"object": "list", "data": ["assistant1"]})
    )
    result = await agent.list_assistants(limit=1)
    assert result["object"] == "list"
    assert "assistant1" in result["data"]

    delattr(client, "assistants")
    with pytest.raises(NotImplementedError):
        await agent.list_assistants()

    return result


@pytest.mark.asyncio
async def test_retrieve_assistant(agent: OpenAIAgent) -> Dict[str, Any]:
    client = cast(Any, agent._client)  # type: ignore
    client.assistants = MagicMock()
    client.assistants.retrieve = AsyncMock(return_value=MagicMock(model_dump=lambda: {"id": "asst_abc123"}))
    result = await agent.retrieve_assistant("asst_abc123")
    assert result["id"] == "asst_abc123"

    delattr(client, "assistants")
    with pytest.raises(NotImplementedError):
        await agent.retrieve_assistant("asst_abc123")

    return result


@pytest.mark.asyncio
async def test_modify_assistant(agent: OpenAIAgent) -> Dict[str, Any]:
    client = cast(Any, agent._client)  # type: ignore
    client.assistants = MagicMock()
    client.assistants.update = AsyncMock(
        return_value=MagicMock(model_dump=lambda: {"id": "asst_123", "name": "newname"})
    )
    result = await agent.modify_assistant("asst_123", name="newname")
    assert result["id"] == "asst_123"
    assert result["name"] == "newname"

    delattr(client, "assistants")
    with pytest.raises(NotImplementedError):
        await agent.modify_assistant("asst_123", name="newname")

    call = FunctionCall(name="not_a_tool", arguments="{}", id="call1")
    exec_result = await agent._execute_tool_call(call, CancellationToken())  # type: ignore
    assert exec_result.is_error

    agent._tool_map["bad_args"] = agent._tool_map["get_weather"]  # type: ignore
    call = FunctionCall(name="bad_args", arguments="{invalid_json}", id="call2")
    exec_result = await agent._execute_tool_call(call, CancellationToken())  # type: ignore
    assert exec_result.is_error and "Invalid JSON" in exec_result.content
    mock_tool = MagicMock(spec=Tool)
    mock_tool.name = "fail_tool"
    mock_tool.run_json = AsyncMock(side_effect=Exception("fail"))
    mock_tool.return_value_as_string = MagicMock(return_value="error string")
    agent._tool_map["fail_tool"] = mock_tool  # type: ignore

    call = FunctionCall(name="fail_tool", arguments="{}", id="call3")
    exec_result = await agent._execute_tool_call(call, CancellationToken())  # type: ignore
    assert exec_result.is_error and "fail" in exec_result.content

    return result


@pytest.mark.asyncio
async def test_on_messages_inner_messages(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    class DummyMsg(BaseChatMessage):
        type: str = "DummyMsg"
        content: str = "dummy content"

        def __init__(self) -> None:
            super().__init__(source="dummy")

        def to_model_message(self) -> UserMessage:
            return UserMessage(content=self.content, source=self.source)

        def to_model_text(self) -> str:
            return self.content

        def to_text(self) -> str:
            return self.content

    dummy_inner = DummyMsg()
    dummy_response = Response(chat_message=TextMessage(source="agent", content="hi"), inner_messages=None)

    async def fake_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[Union[BaseChatMessage, Response], None]:
        yield dummy_inner
        yield dummy_response

    with patch.object(agent, "on_messages_stream", fake_stream):
        response = await agent.on_messages([TextMessage(source="user", content="test")], cancellation_token)
        assert response.chat_message is not None
        assert isinstance(response.chat_message, TextMessage)
        assert response.chat_message.content == "hi"
        assert response.inner_messages is not None
        assert dummy_inner in response.inner_messages


@pytest.mark.asyncio
async def test_build_api_params(agent: OpenAIAgent) -> None:
    agent._last_response_id = None  # type: ignore
    params = agent._build_api_parameters([{"role": "user", "content": "hi"}])  # type: ignore
    assert "previous_response_id" not in params
    agent._last_response_id = "resp-456"  # type: ignore
    params = agent._build_api_parameters([{"role": "user", "content": "hi"}])  # type: ignore
    assert params.get("previous_response_id") == "resp-456"

    assert "max_tokens" not in params
    assert params.get("max_output_tokens") == 1000

    assert params.get("store") is True
    assert params.get("truncation") == "auto"

    agent._json_mode = True  # type: ignore
    params = agent._build_api_parameters([{"role": "user", "content": "hi"}])  # type: ignore
    assert "text.format" not in params
    assert params.get("text") == {"type": "json_object"}


@pytest.mark.asyncio
async def test_delete_assistant(agent: OpenAIAgent) -> Dict[str, Any]:
    client = cast(Any, agent._client)  # type: ignore
    client.assistants = MagicMock()
    client.assistants.delete = AsyncMock(return_value=MagicMock(model_dump=lambda: {"id": "asst_123"}))
    result = await agent.delete_assistant("asst_123")
    assert result["id"] == "asst_123"
    delattr(client, "assistants")
    with pytest.raises(NotImplementedError):
        await agent.delete_assistant("asst_123")

    return result


@pytest.mark.asyncio
async def test_on_messages_previous_response_id(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    message = TextMessage(source="user", content="hi")
    response = await agent.on_messages([message], cancellation_token)
    assert response.chat_message is not None
    assert isinstance(response.chat_message, TextMessage)
    message = TextMessage(source="user", content="hi")
    response = await agent.on_messages([message], cancellation_token)
    assert response.chat_message is not None
    assert isinstance(response.chat_message, TextMessage)


@pytest.mark.asyncio
async def test_on_messages_stream(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    dummy_response = Response(chat_message=TextMessage(source="agent", content="hi"), inner_messages=None)

    async def fake_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[Response, None]:
        yield dummy_response

    with patch.object(agent, "on_messages_stream", fake_stream):
        resp = await agent.on_messages([TextMessage(source="user", content="hi")], cancellation_token)
        assert isinstance(resp.chat_message, TextMessage)
        assert resp.chat_message.content == "hi"


@pytest.mark.asyncio
async def test_component_serialization(agent: OpenAIAgent) -> None:
    config = agent.dump_component()
    config_dict: Any = None
    if isinstance(config, dict):
        config_dict = config
    elif hasattr(config, "model_dump_json"):
        config_dict = json.loads(config.model_dump_json())
    elif hasattr(config, "model_dump"):
        config_dict = config.model_dump()
    elif isinstance(config, str):
        config_dict = json.loads(config)
    else:
        config_dict = {"name": agent.name, "description": agent.description}

    if isinstance(config_dict, dict) and "config" in config_dict:
        config_dict = config_dict["config"]

    assert config_dict["name"] == "assistant"
    assert config_dict["description"] == "Test assistant using the Response API"
    assert config_dict["model"] == "gpt-4o"
    assert config_dict["instructions"] == "You are a helpful AI assistant."
    assert config_dict["temperature"] == 0.7
    assert config_dict["max_output_tokens"] == 1000
    assert config_dict["store"] is True
    assert config_dict["truncation"] == "auto"


@pytest.mark.asyncio
async def test_from_config(agent: OpenAIAgent) -> None:
    config = agent.dump_component()

    config_dict: Dict[str, Any] = {}
    if hasattr(config, "model_dump_json"):
        config_dict = json.loads(config.model_dump_json())
    elif isinstance(config, str):
        config_dict = json.loads(config)
    elif isinstance(config, dict):
        config_dict = config

    if "tools" in config_dict and config_dict["tools"] is not None:
        serialized_tools: List[Dict[str, Any]] = []
        tools_any: Any = config_dict["tools"]
        if isinstance(tools_any, list):
            tools_list: List[Any] = cast(List[Any], tools_any)  # type: ignore[redundant-cast]
            tools_count: int = len(tools_list)
            for i in range(tools_count):
                tool_any: Any = tools_list[i]
                tool_dict: Dict[str, Any] = {}
                if isinstance(tool_any, dict):
                    tool_dict = tool_any
                elif tool_any is not None and isinstance(tool_any, object) and hasattr(tool_any, "model_dump"):
                    model_dump_any: Any = getattr(tool_any, "model_dump", None)
                    if callable(model_dump_any):
                        try:
                            result_any: Any = model_dump_any()
                            if isinstance(result_any, dict):
                                tool_dict = result_any
                            else:
                                tool_dict = {"provider": "unknown", "config": {}}
                        except Exception:
                            tool_dict = {"provider": "unknown", "config": {}}
                    else:
                        tool_dict = {"provider": "unknown", "config": {}}
                else:
                    tool_dict = {"provider": "unknown", "config": {}}
                serialized_tools.append(tool_dict)
            config_dict["tools"] = serialized_tools

    with patch("openai.AsyncOpenAI"):
        loaded_agent = OpenAIAgent.load_component(config_dict)

        assert loaded_agent.name == "assistant"
        assert loaded_agent.description == "Test assistant using the Response API"
        assert loaded_agent._model == "gpt-4o"  # type: ignore
        assert loaded_agent._instructions == "You are a helpful AI assistant."  # type: ignore
        assert loaded_agent._temperature == 0.7  # type: ignore
        assert loaded_agent._max_output_tokens == 1000  # type: ignore
        assert loaded_agent._store is True  # type: ignore
        assert loaded_agent._truncation == "auto"  # type: ignore


@pytest.mark.asyncio
async def test_multimodal_message_response(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    # Test that the multimodal message is converted to the correct format
    img = Image.from_base64(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
    )
    multimodal_message = MultiModalMessage(content=["Can you describe the content of this image?", img], source="user")

    # Patch client.responses.create to simulate image-capable output
    async def mock_responses_create(**kwargs: Any) -> Any:
        class MockResponse:
            def __init__(self) -> None:
                self.output_text = "I see a cat in the image."
                self.id = "resp-image-001"

        return MockResponse()

    agent._client.responses.create = AsyncMock(side_effect=mock_responses_create)  # type: ignore

    response = await agent.on_messages([multimodal_message], cancellation_token)

    assert response.chat_message is not None
    assert isinstance(response.chat_message, TextMessage)
    assert "cat" in response.chat_message.content.lower()
