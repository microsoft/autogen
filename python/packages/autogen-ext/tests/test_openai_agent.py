import json
import os
from typing import Any, AsyncGenerator, Dict, List, Mapping, Optional, Sequence, Union, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_agentchat.messages import (
    BaseChatMessage,
    MultiModalMessage, 
    TextMessage, 
    ToolCallExecutionEvent, 
    ToolCallRequestEvent
)
from autogen_agentchat.messages import Image
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import AssistantMessage, SystemMessage, UserMessage
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.agents.openai import OpenAIAgent
from autogen_ext.agents.openai._openai_agent import FunctionExecutionResult
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

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
    client = AsyncMock(spec=AsyncOpenAI)
    beta = MagicMock()
    client.beta = beta
    beta.chat = MagicMock()
    beta.chat.completions = MagicMock()

    async def mock_create_stream(**kwargs: Any) -> AsyncGenerator[FakeChunk, None]:
        if "tools" in kwargs and kwargs["tools"]:
            yield FakeChunk(
                choices=[
                    FakeChunkChoice(
                        delta=FakeChunkDelta(
                            tool_calls=[FakeToolCall(id="call-1", function=FakeToolCallFunction(name="get_weather"))]
                        )
                    )
                ]
            )
            yield FakeChunk(
                choices=[
                    FakeChunkChoice(
                        delta=FakeChunkDelta(
                            tool_calls=[
                                FakeToolCall(
                                    id="call-1", function=FakeToolCallFunction(arguments='{"location":"New York"}')
                                )
                            ]
                        )
                    )
                ]
            )
            yield FakeChunk(choices=[FakeChunkChoice(finish_reason="tool_calls")])
        else:
            yield FakeChunk(choices=[FakeChunkChoice(delta=FakeChunkDelta(content="Hello"))])
            yield FakeChunk(choices=[FakeChunkChoice(delta=FakeChunkDelta(content=" world!"))])
            yield FakeChunk(choices=[FakeChunkChoice(finish_reason="stop")])

    beta.chat.completions.create = AsyncMock(side_effect=mock_create_stream)
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

    beta.chat.completions.create = AsyncMock(side_effect=mock_create_error)
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
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The location to get weather for"
                    }
                },
                "required": ["location"]
            }
        )

    @property
    def args_type(self) -> type:
        return GetWeatherArgs

    @property
    def state_type(self) -> type[BaseModel] | None:
        return None
        
    @property
    def description(self) -> str:
        return "Get the current weather in a location"

    @property
    def name(self) -> str:
        return self._name
        
    @property
    def return_type(self) -> type:
        return WeatherResponse
    
    @property
    def schema(self) -> ToolSchema:
        return self._schema
        
    async def load_state_json(self, state_json: Mapping[str, Any]) -> None:
        pass
    
    async def save_state_json(self) -> Dict[str, Any]:
        return {}
    
    def return_value_as_string(self, result: Any) -> str:
        if isinstance(result, dict):
            return json.dumps(result)
        return str(result)
        
    async def run_json(self, json_args: Mapping[str, Any], cancellation_token: CancellationToken) -> Dict[str, Any]:
        _ = GetWeatherArgs(**json_args)
        return WeatherResponse(temperature=72.5, conditions="sunny").model_dump()

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
        max_tokens=1000,
        seed=42,
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
    message = TextMessage(source="user", content="Hello, how are you?")
    response = await agent.on_messages([message], cancellation_token)

    assert response.chat_message is not None
    assert isinstance(response.chat_message, TextMessage)
    assert response.chat_message.content == "Hello world!"
    assert response.chat_message.source == "assistant"

@pytest.mark.asyncio
async def test_different_message_types(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    messages = [
        TextMessage(content="Hello from user", source="user"),
        TextMessage(content="System instruction", source="system"),
        TextMessage(content="Previous assistant response", source="assistant"),
    ]

    response = await agent.on_messages(messages, cancellation_token)
    assert response.chat_message is not None
    assert isinstance(response.chat_message, TextMessage)
    assert response.chat_message.content == "Hello world!"

@pytest.mark.asyncio
async def test_multimodal_message(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    message = MultiModalMessage(
        source="user", content=["This is a multimodal message"]
    )

    response = await agent.on_messages([message], cancellation_token)
    assert response.chat_message is not None
    assert isinstance(response.chat_message, TextMessage)  
    assert response.chat_message.content == "Hello world!"

@pytest.mark.asyncio
async def test_tool_calling(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    async def mock_run_json(self: Any, json_args: Dict[str, Any], cancellation_token: CancellationToken) -> Dict[str, Any]:
        return {"temperature": 75.0, "conditions": "sunny and clear"}

    with patch.object(WeatherTool, "run_json", mock_run_json):
        message = TextMessage(source="user", content="What's the weather in New York?")

        all_messages = []
        async for msg in agent.on_messages_stream([message], cancellation_token):
            all_messages.append(msg)

        assert any(isinstance(msg, ToolCallRequestEvent) for msg in all_messages)
        assert any(isinstance(msg, ToolCallExecutionEvent) for msg in all_messages)

        final_response = next((msg for msg in all_messages if hasattr(msg, "chat_message")), None)
        assert final_response is not None

        assert hasattr(final_response, "inner_messages")
        assert final_response.inner_messages is not None
        assert len(final_response.inner_messages) > 0

@pytest.mark.asyncio
async def test_failing_tool(agent: OpenAIAgent, failing_tool: Tool, cancellation_token: CancellationToken) -> None:
    agent._tools.append(
        {
            "type": "function",
            "function": {
                "name": failing_tool.name,
                "description": "A tool that always fails",
                "parameters": {"type": "object", "properties": {}}},
        }
    )
    agent._tool_map[failing_tool.name] = failing_tool

    tool_call = FunctionCall(id="call-123", name=failing_tool.name, arguments="{}")

    result = await agent._execute_tool_call(tool_call, cancellation_token)

    assert result.is_error
    assert "Error: " in result.content
    assert result.name == failing_tool.name
    assert result.call_id == "call-123"

@pytest.mark.asyncio
async def test_invalid_tool_name(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    tool_call = FunctionCall(id="call-123", name="non_existent_tool", arguments="{}")

    result = await agent._execute_tool_call(tool_call, cancellation_token)

    assert result.is_error
    assert "Error: Tool 'non_existent_tool' is not available" in result.content
    assert result.name == "non_existent_tool"

@pytest.mark.asyncio
async def test_json_mode(json_mode_agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    message = TextMessage(source="user", content="Give me JSON data")

    api_params = json_mode_agent._build_api_parameters([{"role": "user", "content": "Give me JSON data"}])

    assert "response_format" in api_params
    assert api_params["response_format"]["type"] == "json_object"

    response = await json_mode_agent.on_messages([message], cancellation_token)
    assert response.chat_message is not None

@pytest.mark.asyncio
async def test_error_handling(error_agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    message = TextMessage(source="user", content="This will cause an error")

    all_messages = []
    async for msg in error_agent.on_messages_stream([message], cancellation_token):
        all_messages.append(msg)

    final_response = next((msg for msg in all_messages if hasattr(msg, "chat_message")), None)
    assert final_response is not None
    assert isinstance(final_response.chat_message, TextMessage)
    assert "Error generating response:" in final_response.chat_message.content

@pytest.mark.asyncio
async def test_state_management(agent: OpenAIAgent, cancellation_token: CancellationToken) -> None:
    agent._last_response_id = "resp-123"
    agent._message_history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there"}]

    state = await agent.save_state()

    new_agent = OpenAIAgent(
        name="assistant2",
        description="Test assistant 2",
        client=agent._client,
        model="gpt-4o",
        instructions="You are a helpful AI assistant.",
    )

    await new_agent.load_state(state)

    assert new_agent._last_response_id == "resp-123"
    assert len(new_agent._message_history) == 2
    assert new_agent._message_history[0]["role"] == "user"
    assert new_agent._message_history[0]["content"] == "Hello"

    await new_agent.on_reset(cancellation_token)
    assert new_agent._last_response_id is None
    assert len(new_agent._message_history) == 0

@pytest.mark.asyncio
async def test_convert_message_functions(agent: OpenAIAgent) -> None:
    from autogen_ext.agents.openai._openai_agent import _convert_message_to_openai_message

    user_msg = TextMessage(content="Hello", source="user")
    openai_user_msg = _convert_message_to_openai_message(user_msg)
    assert openai_user_msg["role"] == "user"
    assert openai_user_msg["content"] == "Hello"

    sys_msg = TextMessage(content="System prompt", source="system")
    openai_sys_msg = _convert_message_to_openai_message(sys_msg)
    assert openai_sys_msg["role"] == "system"
    assert openai_sys_msg["content"] == "System prompt"

    assistant_msg = TextMessage(content="Assistant reply", source="assistant")
    openai_assistant_msg = _convert_message_to_openai_message(assistant_msg)
    assert openai_assistant_msg["role"] == "assistant"
    assert openai_assistant_msg["content"] == "Assistant reply"

    text_msg = TextMessage(content="Plain text", source="other")
    openai_text_msg = _convert_message_to_openai_message(text_msg)
    assert openai_text_msg["role"] == "user"
    assert openai_text_msg["content"] == "Plain text"

@pytest.mark.asyncio
async def test_tool_schema_conversion(agent: OpenAIAgent) -> None:
    from autogen_ext.agents.openai._openai_agent import _convert_tool_to_function_schema

    tool_schema = _convert_tool_to_function_schema(agent._tool_map["get_weather"])

    assert tool_schema["name"] == "get_weather"
    assert "description" in tool_schema
    assert "parameters" in tool_schema
    assert tool_schema["parameters"]["type"] == "object"
    assert "properties" in tool_schema["parameters"]

@pytest.mark.asyncio
async def test_component_serialization(agent: OpenAIAgent) -> None:
    config = agent.dump_component()

    config_str = config if isinstance(config, str) else str(config)
    config_dict = json.loads(config_str)

    assert config_dict["name"] == "assistant"
    assert config_dict["description"] == "Test assistant using the Response API"
    assert config_dict["model"] == "gpt-4o"
    assert config_dict["instructions"] == "You are a helpful AI assistant."
    assert config_dict["temperature"] == 0.7
    assert config_dict["max_tokens"] == 1000
    assert config_dict["seed"] == 42

@pytest.mark.asyncio
async def test_from_config(agent: OpenAIAgent) -> None:
    config = agent.dump_component()

    with patch("openai.AsyncOpenAI"):
        loaded_agent = OpenAIAgent.load_component(config)

        assert loaded_agent.name == "assistant"
        assert loaded_agent.description == "Test assistant using the Response API"
        assert loaded_agent._model == "gpt-4o"
        assert loaded_agent._instructions == "You are a helpful AI assistant."
        assert loaded_agent._temperature == 0.7
        assert loaded_agent._max_tokens == 1000
        assert loaded_agent._seed == 42
