import asyncio
import inspect
import json
import logging
import os
import random
from asyncio import Task
from copy import deepcopy
from typing import Sequence, Optional, Mapping, Any, List, Union, Unpack, AsyncGenerator

import google.generativeai as genai
from google.ai.generativelanguage import (
    Part,
    FunctionCall as GLFunctionCall,
    FunctionResponse as GLFunctionResponse,
)
from google.generativeai.types import answer_types
from google.generativeai.types import content_types
from google.generativeai.types import generation_types

from autogen_agentchat import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from autogen_core.application.logging.events import LLMCallEvent
from autogen_core.base import CancellationToken
from autogen_core.components import FunctionCall
from autogen_core.components.models import (
    ChatCompletionClient,
    LLMMessage,
    CreateResult,
    RequestUsage,
    UserMessage,
    SystemMessage,
    AssistantMessage,
    FunctionExecutionResultMessage,
    ModelCapabilities,
    FinishReasons,
    ChatCompletionTokenLogprob,
)
from autogen_core.components.tools import Tool, ToolSchema
from . import _model_info
from .config import GeminiClientConfiguration

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)


gemini_init_kwargs = set(inspect.getfullargspec(genai.GenerativeModel.__init__).args)
gemini_init_kwargs.remove("self")

create_kwargs = set(inspect.getfullargspec(genai.GenerationConfig.__init__).args)
create_kwargs.remove("self")


class GeminiChatCompletionClient(ChatCompletionClient):
    def __init__(self, **kwargs: Unpack[GeminiClientConfiguration]):
        self.api_key = kwargs.pop("api_key", None)
        self.use_vertexai = False

        if not self.api_key:
            self.api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
            if self.api_key is None:
                self.use_vertexai = True
                self._init_vertexai(**kwargs)

        if not self.use_vertexai:
            assert ("project_id" not in kwargs) and (
                "location" not in kwargs
            ), "Google Cloud project and compute location cannot be set when using an API Key!"

        if "model" in kwargs:
            self._model_name = kwargs.pop("model")
        else:
            self._model_name = inspect.signature(genai.GenerativeModel.__init__).parameters["model_name"].default

        self._model_capabilities = _model_info.get_capabilities(self._model_name)

        # Filter only relevant keys for `_create_args` and the client
        self._create_args = {
            k: (self.convert_tools(v) if k == "tools" else v)
            for k, v in kwargs.items()
            if k in gemini_init_kwargs
        }

        if self.use_vertexai:
            raise NotImplementedError()
        else:
            self._client = genai.GenerativeModel(model_name=self._model_name, **self._create_args)

        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        create_args = dict(extra_create_args).copy()

        if json_output is not None:
            if self.capabilities["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True:
                if len(tools) > 0:
                    raise ValueError("Function calling with a response mime type: 'application/json' is unsupported")
                create_args["response_mime_type"] = "application/json"

        if self.capabilities["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output")

        if self.capabilities["function_calling"] is False and (
            # TODO: Maybe encapsulate this in a function
            len(tools) > 0 or len(self._create_args.get("tools", [])) > 0
        ):
            raise ValueError("Model does not support function calling")

        gemini_messages: Sequence[content_types.ContentType] = self._to_gemini_messages(messages)

        future: Task[generation_types.AsyncGenerateContentResponse]

        # Args needed:
        # config_args
        # start_chat args
        # completions args
        if self.use_vertexai:
            raise NotImplementedError()
        else:
            generation_config = genai.GenerationConfig(**create_args)
            genai.configure(api_key=self.api_key)
            # TODO: Make enable_automatic_function_calling configurable
            chat = self._client.start_chat(history=gemini_messages[:-1], enable_automatic_function_calling=False)

        if len(tools) > 0 or len(self._create_args.get("tools", [])) > 0:
            gemini_tools = self.convert_tools(tools)
            future = asyncio.ensure_future(
                chat.send_message_async(
                    content=gemini_messages[-1],
                    tools=gemini_tools,
                    generation_config=generation_config,
                    stream=False,
                )
            )
        else:
            future = asyncio.ensure_future(
                chat.send_message_async(
                    content=gemini_messages[-1],
                    generation_config=generation_config,
                    stream=False,
                )
            )

        if cancellation_token is not None:
            await cancellation_token.link_future(future)

        result = await future

        if result.usage_metadata is not None:
            logger.info(
                LLMCallEvent(
                    prompt_tokens=result.usage_metadata.prompt_token_count,
                    completion_tokens=result.usage_metadata.candidates_token_count,
                )
            )

        usage = RequestUsage(
            prompt_tokens=result.usage_metadata.prompt_token_count if result.usage_metadata is not None else 0,
            completion_tokens=result.usage_metadata.candidates_token_count if result.usage_metadata is not None else 0,
        )

        choice = result.candidates[0]
        finish_reason: Optional[FinishReasons] = None
        content: Union[str, List[FunctionCall]] = ""

        for part in result.parts:
            # TODO: Handle support for call_extensions
            if func := part.function_call:
                content = [
                    FunctionCall(
                        id="".join([func.name, "_", str(random.randint(0, 1000))]),
                        arguments=json.dumps(dict(func.args)),
                        name=func.name,
                    )
                ]
                finish_reason = "function_calls"
            else:
                content = part.text or ""
                finish_reason = self.get_finish_reason(choice.finish_reason)

        # TODO: Add logprobs support
        logprobs: Optional[List[ChatCompletionTokenLogprob]] = None

        if finish_reason is not None:
            response = CreateResult(
                finish_reason=finish_reason,
                content=content,
                usage=usage,
                cached=False,
                logprobs=logprobs,
            )
        else:
            raise ValueError("Finish reason is not set")

        return response

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        raise NotImplementedError()

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def count_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        # TODO: Implement token counting with VertexAI
        if self.use_vertexai:
            raise NotImplementedError()
        else:
            genai.configure(api_key=self.api_key)
            gemini_messages = self._to_gemini_messages(messages)
            gemini_tools = self.convert_tools(tools)
            result = self._client.count_tokens(gemini_messages, tools=gemini_tools)
            return result.total_tokens

    def remaining_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        token_limit = _model_info.get_token_limit(self._create_args["model"])
        return token_limit - self.count_tokens(messages, tools)

    @staticmethod
    def _user_message_to_gemini_message(message: Union[SystemMessage, UserMessage]) -> content_types.ContentType:
        return {
            "parts": [Part({"text": message.content})],
            "role": "user",
        }

    @staticmethod
    def _assistant_message_to_gemini_message(message: AssistantMessage) -> content_types.ContentType:
        if isinstance(message.content[0], FunctionCall):
            return {
                "parts": [
                    Part(
                        function_call=GLFunctionCall(  # type: ignore
                            name=message.content[0].name,
                            args=json.loads(message.content[0].arguments),
                        )
                    )
                ],
                "role": "user",
            }
        else:
            return {
                "parts": [Part({"text": message.content})],
                "role": "user",
            }

    @staticmethod
    def _to_gemini_function_message(message: FunctionExecutionResultMessage, history) -> content_types.ContentType:
        name = next(
            c.name
            for m in history
            if isinstance(m, AssistantMessage)
            for c in m.content
            if isinstance(c, FunctionCall) and message.content[0].call_id == c.id
        ), None

        if name is None:
            raise ValueError(f"Function call with id '{message.content[0].call_id}' not found in history")

        return {
            "parts": [
                Part(
                    function_response=GLFunctionResponse(  # type: ignore
                        name=name,
                        response={
                            "result": GeminiChatCompletionClient._to_json(message.content[0].content),
                        },
                    )
                )
            ],
            "role": "user",
        }

    def to_gemini_message(self, message: LLMMessage, history) -> content_types.ContentType:
        if isinstance(message, (SystemMessage | UserMessage)):
            return self._user_message_to_gemini_message(message)
        elif isinstance(message, AssistantMessage):
            return self._assistant_message_to_gemini_message(message)
        elif isinstance(message, FunctionExecutionResultMessage):
            return self._to_gemini_function_message(message, history)

    def _to_gemini_messages(self, messages: Sequence[LLMMessage]) -> Sequence[content_types.ContentType]:
        return [self.to_gemini_message(msg, messages) for msg in messages]

    def _init_vertexai(self, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def _to_json(content):
        try:
            return json.loads(content)
        except ValueError:
            return content

    @staticmethod
    def get_finish_reason(finish_reason: answer_types.FinishReason) -> FinishReasons:
        match finish_reason:
            case answer_types.FinishReason.FINISH_REASON_UNSPECIFIED | answer_types.FinishReason.STOP:
                return "stop"
            case answer_types.FinishReason.MAX_TOKENS:
                return "length"
            case (
                answer_types.FinishReason.SAFETY
                | answer_types.FinishReason.RECITATION
                | answer_types.FinishReason.OTHER
                | answer_types.FinishReason.LANGUAGE
                | answer_types.FinishReason.BLOCKLIST
                | answer_types.FinishReason.PROHIBITED_CONTENT
                | answer_types.FinishReason.SPII
                | answer_types.FinishReason.MALFORMED_FUNCTION_CALL
            ):
                return "content_filter"
            case _:
                raise ValueError(f"Unknown finish reason: {finish_reason.name}")

    @staticmethod
    def convert_tools(tools: Sequence[Tool | ToolSchema]) -> List[content_types.FunctionLibraryType]:
        result = []
        for tool in tools:
            if isinstance(tool, Tool):
                tool_schema = tool.schema
            else:
                assert isinstance(tool, dict)
                tool_schema = tool

            params = deepcopy(tool_schema["parameters"])
            for key, _ in params["properties"].items():
                if "title" in params["properties"][key]:
                    del params["properties"][key]["title"]

            function_declaration_args = {"name": tool_schema["name"], "description": tool_schema["description"]}
            if params["properties"]:
                function_declaration_args["parameters"] = params

            result.append(content_types.FunctionDeclaration(**function_declaration_args))

        return result

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._model_capabilities
