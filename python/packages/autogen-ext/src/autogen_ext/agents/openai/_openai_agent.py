import asyncio
import json
import logging
import warnings
from typing import Any, AsyncGenerator, Dict, List, Mapping, Optional, Sequence, Type, Union, cast, Tuple

from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    AgentEvent,
    BaseChatMessage,
    ChatMessage, 
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
    HandoffMessage
)
from autogen_core import CancellationToken, Component, ComponentModel, FunctionCall
from autogen_core.models import AssistantMessage, ChatCompletionClient, LLMMessage, SystemMessage, UserMessage
from autogen_core.tools import FunctionTool, Tool, ToolSchema
from pydantic import BaseModel, Field

from openai import AsyncAzureOpenAI, AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


def _convert_tool_to_function_schema(tool: Tool) -> Dict[str, Any]:
    schema = tool.schema
    parameters: Dict[str, object] = {}
    if "parameters" in schema:
        parameters = {
            "type": schema["parameters"]["type"],
            "properties": schema["parameters"]["properties"],
        }
        if "required" in schema["parameters"]:
            parameters["required"] = schema["parameters"]["required"]

    return {
        "name": schema["name"],
        "description": schema.get("description", ""),
        "parameters": parameters,
    }


def _convert_message_to_openai_message(message: Union[TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage]) -> Dict[str, Any]:
    """Convert an AutoGen message to an OpenAI message format."""
    if isinstance(message, TextMessage):
        if message.source == "user":
            return {"role": "user", "content": str(message.content)}
        elif message.source == "system":
            return {"role": "system", "content": str(message.content)}
        elif message.source == "assistant":
            return {"role": "assistant", "content": str(message.content)}
        else:
            # Default to user role for other sources
            return {"role": "user", "content": str(message.content)}
    elif isinstance(message, MultiModalMessage):
        content_parts = []
        for part in message.content:
            if isinstance(part, TextMessage):
                content_parts.append({"type": "text", "text": str(part.content)})
            elif isinstance(part, ImageMessage):
                image_url = str(part.content)
                content_parts.append({"type": "image_url", "image_url": {"url": image_url}})
        # Return as a properly typed dictionary instead of relying on structural typing
        return {"role": "user", "content": content_parts}
    else:
        # Default handling for other message types
        return {"role": "user", "content": str(message.content)}


class OpenAIAgentState(BaseModel):
    type: str = Field(default="OpenAIAgentState")
    response_id: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


class OpenAIAgentConfig(BaseModel):
    name: str
    description: str
    model: str
    instructions: str
    tools: List[ComponentModel] | None = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    seed: Optional[int] = None
    json_mode: bool = False


class FunctionExecutionResult(BaseModel):
    """Result of a function execution."""
    content: str
    call_id: str
    name: str
    is_error: bool = False


class OpenAIAgent(BaseChatAgent, Component[OpenAIAgentConfig]):
    component_config_schema = OpenAIAgentConfig
    component_provider_override = "autogen_ext.agents.openai.OpenAIAgent"

    def __init__(
        self,
        name: str,
        description: str,
        client: Union[AsyncOpenAI, AsyncAzureOpenAI],
        model: str,
        instructions: str,
        tools: Optional[List[Tool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        seed: Optional[int] = None,
        json_mode: bool = False,
    ) -> None:
        super().__init__(name, description)

        if isinstance(client, ChatCompletionClient):
            raise ValueError(
                "Please use an OpenAI AsyncClient instance instead of an AutoGen ChatCompletionClient instance."
            )

        self._client = client
        self._model = model
        self._instructions = instructions
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._seed = seed
        self._json_mode = json_mode

        self._last_response_id: Optional[str] = None
        self._message_history: List[Dict[str, Any]] = []

        self._tools: List[Dict[str, Any]] = []
        self._tool_map: Dict[str, Tool] = {}

        if tools:
            for tool in tools:
                function_schema = {"type": "function", "function": _convert_tool_to_function_schema(tool)}
                self._tools.append(function_schema)
                self._tool_map[tool.name] = tool

    @property
    def produced_message_types(self) -> Sequence[Type[BaseChatMessage]]:
        """Return the types of messages that this agent can produce."""
        return [TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage]

    async def _execute_tool_call(
        self, tool_call: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        tool_name = tool_call.name
        if tool_name not in self._tool_map:
            return FunctionExecutionResult(
                content=f"Error: Tool '{tool_name}' is not available",
                call_id=tool_call.id,
                name=tool_name,
                is_error=True,
            )

        tool = self._tool_map[tool_name]
        try:
            try:
                arguments = json.loads(tool_call.arguments)
            except json.JSONDecodeError as json_err:
                return FunctionExecutionResult(
                    content=f"Error: Invalid JSON in tool arguments - {str(json_err)}",
                    call_id=tool_call.id,
                    name=tool_name,
                    is_error=True,
                )

            result = await tool.run_json(arguments, cancellation_token)
            return FunctionExecutionResult(
                content=tool.return_value_as_string(result), call_id=tool_call.id, name=tool_name, is_error=False
            )
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            event_logger.warning(f"Tool execution error in {tool_name}: {error_msg}")
            return FunctionExecutionResult(content=error_msg, call_id=tool_call.id, name=tool_name, is_error=True)

    def _build_api_parameters(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        has_system_message = any(msg.get("role") == "system" for msg in messages)

        if self._instructions and not has_system_message:
            messages = [{"role": "system", "content": self._instructions}] + messages

        api_params: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }

        if self._temperature is not None:
            api_params["temperature"] = self._temperature

        if self._max_tokens is not None:
            api_params["max_tokens"] = self._max_tokens

        if self._seed is not None:
            api_params["seed"] = self._seed

        if self._tools:
            api_params["tools"] = self._tools

        if self._json_mode:
            api_params["response_format"] = {"type": "json_object"}

        return api_params

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        response = None
        inner_messages: List[Union[AgentEvent, BaseChatMessage]] = []

        async for msg in self.on_messages_stream(messages, cancellation_token):
            if isinstance(msg, Response):
                response = msg
            elif not isinstance(msg, ModelClientStreamingChunkEvent):
                inner_messages.append(msg)

        if response is None:
            raise ValueError("No response was generated")

        # Ensure inner_messages is initialized in the response
        if response.inner_messages is None:
            response.inner_messages = []
            
        # Add any messages not already in response.inner_messages
        for msg in inner_messages:
            if msg not in response.inner_messages:
                response.inner_messages.append(msg)

        return response

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | BaseChatMessage | Response, None]:
        input_messages: List[Dict[str, Any]] = []

        if self._message_history:
            input_messages.extend(self._message_history)

        # Use proper type casting for each message
        for message in messages:
            # Only try to convert compatible message types
            if isinstance(message, (TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage)):
                openai_message = _convert_message_to_openai_message(message)
                input_messages.append(openai_message)
            else:
                # Fall back to a simple text representation for unsupported message types
                input_messages.append({"role": "user", "content": str(message.content)})

        # Update message history with proper casting for each message
        for message in messages:
            if isinstance(message, (TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage)):
                self._message_history.append(_convert_message_to_openai_message(message))
            else:
                # Fall back to a simple text representation for unsupported message types
                self._message_history.append({"role": "user", "content": str(message.content)})

        inner_messages: List[AgentEvent | ChatMessage] = []

        api_params = self._build_api_parameters(input_messages)

        try:
            completion = await cancellation_token.link_future(
                asyncio.ensure_future(self._client.chat.completions.create(stream=True, **api_params))
            )

            content_buffer = []
            current_function_calls = {}
            last_chunk_id = None

            async for chunk in completion:
                if hasattr(chunk, "id"):
                    last_chunk_id = chunk.id

                if not hasattr(chunk, "choices") or not chunk.choices:
                    event_logger.warning(f"Received malformed chunk without choices: {chunk}")
                    continue

                delta = chunk.choices[0].delta

                if hasattr(delta, "content") and delta.content:
                    content_buffer.append(delta.content)
                    yield ModelClientStreamingChunkEvent(source=self.name, content=delta.content)

                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        if not hasattr(tool_call, "id") or not tool_call.id:
                            event_logger.warning(f"Received tool call without ID: {tool_call}")
                            continue

                        call_id = tool_call.id
                        if call_id not in current_function_calls:
                            # Initialize with empty dictionary structure
                            current_function_calls[call_id] = {
                                "id": tool_call.id or "",
                                "function": {
                                    "name": tool_call.function.name or "",
                                    "arguments": tool_call.function.arguments or "",
                                },
                            }
                        else:
                            # Get the current call info
                            current_call = current_function_calls[call_id]
                            # Update function properties safely
                            if hasattr(tool_call.function, "name") and tool_call.function.name:
                                current_call["function"]["name"] = tool_call.function.name
                            if hasattr(tool_call.function, "arguments") and tool_call.function.arguments:
                                args = current_call["function"].get("arguments", "")
                                current_call["function"]["arguments"] = args + (tool_call.function.arguments or "")

            if current_function_calls:
                function_calls: List[FunctionCall] = []

                for call_id, call_info in current_function_calls.items():
                    function_calls.append(
                        FunctionCall(
                            id=call_id, name=call_info["function"]["name"], arguments=call_info["function"]["arguments"]
                        )
                    )

                tool_call_msg = ToolCallRequestEvent(source=self.name, content=function_calls)
                inner_messages.append(tool_call_msg)
                event_logger.debug(tool_call_msg)
                yield tool_call_msg

                tool_results: List[FunctionExecutionResult] = []

                for function_call in function_calls:
                    result = await self._execute_tool_call(function_call, cancellation_token)
                    tool_results.append(result)

                # Convert our FunctionExecutionResult to autogen_core.models FunctionExecutionResult
                from autogen_core.models._types import FunctionExecutionResult as CoreFunctionExecutionResult
                
                core_results = []
                for result in tool_results:
                    core_results.append(
                        CoreFunctionExecutionResult(
                            content=result.content,
                            call_id=result.call_id,
                            name=result.name,
                            is_error=result.is_error
                        )
                    )

                tool_result_msg = ToolCallExecutionEvent(source=self.name, content=core_results)
                inner_messages.append(tool_result_msg)
                event_logger.debug(tool_result_msg)
                yield tool_result_msg

                self._message_history.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {"id": fc.id, "type": "function", "function": {"name": fc.name, "arguments": fc.arguments}}
                            for fc in function_calls
                        ],
                    }
                )

                for result in tool_results:
                    self._message_history.append(
                        {"role": "tool", "tool_call_id": result.call_id, "content": result.content}
                    )

                final_params = self._build_api_parameters(self._message_history)

                try:
                    final_completion = await cancellation_token.link_future(
                        asyncio.ensure_future(self._client.chat.completions.create(stream=True, **final_params))
                    )

                    final_content_buffer = []
                    async for chunk in final_completion:
                        if hasattr(chunk, "id"):
                            last_chunk_id = chunk.id

                        if not hasattr(chunk, "choices") or not chunk.choices:
                            continue

                        delta = chunk.choices[0].delta

                        if hasattr(delta, "content") and delta.content:
                            final_content_buffer.append(delta.content)
                            yield ModelClientStreamingChunkEvent(source=self.name, content=delta.content)

                    content = "".join(final_content_buffer)

                    self._message_history.append({"role": "assistant", "content": content})

                    final_message = TextMessage(source=self.name, content=content)
                    self._last_response_id = last_chunk_id
                    response = Response(chat_message=final_message, inner_messages=inner_messages)
                    yield response

                except Exception as tool_follow_up_error:
                    error_message = f"Error generating response after tool execution: {str(tool_follow_up_error)}"
                    event_logger.error(error_message)
                    error_response = TextMessage(source=self.name, content=error_message)
                    yield Response(chat_message=error_response, inner_messages=inner_messages)

            else:
                content = "".join(content_buffer)

                self._message_history.append({"role": "assistant", "content": content})

                final_message = TextMessage(source=self.name, content=content)
                self._last_response_id = last_chunk_id
                response = Response(chat_message=final_message, inner_messages=inner_messages)
                yield response

        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            event_logger.error(f"API error: {error_message}", exc_info=True)
            error_response = TextMessage(source=self.name, content=error_message)
            yield Response(chat_message=error_response, inner_messages=inner_messages)

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self._last_response_id = None
        self._message_history = []

    async def save_state(self) -> Mapping[str, Any]:
        state = OpenAIAgentState(
            response_id=self._last_response_id,
            history=self._message_history,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        agent_state = OpenAIAgentState.model_validate(state)
        self._last_response_id = agent_state.response_id
        self._message_history = agent_state.history

    def _to_config(self) -> OpenAIAgentConfig:
        """Convert the OpenAI agent to a declarative config."""
        tool_configs = None
        if self._tool_map:
            # Serialize tools as dictionaries instead of using dump_component
            tool_configs = []
            for tool in self._tool_map.values():
                if hasattr(tool, "dump_component"):
                    tool_configs.append(tool.dump_component())
                else:
                    # Fallback for tools without dump_component
                    tool_configs.append({"name": tool.name, "description": getattr(tool, "description", "")})
                    
        return OpenAIAgentConfig(
            name=self.name,
            description=self.description,
            model=self._model,
            instructions=self._instructions,
            tools=tool_configs,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            seed=self._seed,
            json_mode=self._json_mode,
        )
        
    @classmethod
    def _from_config(cls, config: OpenAIAgentConfig) -> 'OpenAIAgent':
        """Create an OpenAI agent from a declarative config."""
        from openai import AsyncOpenAI
        
        # Create a default client since we can't serialize the client in the config
        client = AsyncOpenAI()
        
        tools = None
        if config.tools:
            tools = []
            for tool_config in config.tools:
                if isinstance(tool_config, dict) and "name" in tool_config:
                    # Create a simple tool from config
                    from autogen_core.tools import FunctionTool
                    
                    async def dummy_func(*args, **kwargs):
                        return "Tool not fully restored"
                    
                    tool = FunctionTool(
                        name=tool_config["name"],
                        description=tool_config.get("description", ""),
                        func=dummy_func
                    )
                    tools.append(tool)
                elif hasattr(Tool, "load_component"):
                    # Use load_component if available
                    tools.append(Tool.load_component(tool_config))
            
        return cls(
            name=config.name,
            description=config.description,
            client=client,
            model=config.model,
            instructions=config.instructions,
            tools=tools,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            seed=config.seed,
            json_mode=config.json_mode,
        )

# Define our own ImageMessage since it's not available
class ImageMessage(BaseChatMessage):
    """A message containing an image."""
    content: str  # URL or base64 string
