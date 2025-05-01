import json
import os
import warnings
from typing import Any, AsyncGenerator, Dict, List, Literal, Mapping, Optional, Sequence, TypedDict, Union

from autogen_core import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    ModelInfo,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel

from .page_logger import PageLogger


class RecordDict(TypedDict):
    mode: Literal["create", "create_stream"]
    messages: List[Mapping[str, Any]]
    response: Dict[str, Any]
    stream: List[Mapping[str, Any]]


class ChatCompletionClientRecorder(ChatCompletionClient):
    """
    A chat completion client that supports fast, large-scale tests of code calling LLM clients.

    Two modes are supported:

      1. "record": delegates to the underlying client while also recording the input messages and responses,
         which are saved to disk when finalize() is called.
      2. "replay": loads previously recorded message and responses from disk, then on each call
         checks that its message matches the recorded message, and returns the recorded response.

    The recorded data is stored as a JSON list of records. Each record is a dictionary with a "mode"
    field (either "create" or "create_stream"), a serialized list of messages, and either a "response" (for
    create calls) or a "stream" (a list of streamed outputs for create_stream calls).

    ReplayChatCompletionClient and ChatCompletionCache do similar things, but with significant differences:

        - ReplayChatCompletionClient replays pre-defined responses in a specified order without recording anything or checking the messages sent to the client.
        - ChatCompletionCache caches responses and replays them for messages that have been seen before, regardless of order, and calls the base client for any uncached messages.
    """

    def __init__(
        self,
        client: ChatCompletionClient,
        mode: Literal["record", "replay"],
        session_file_path: str,
        logger: PageLogger | None = None,
    ) -> None:
        if logger is None:
            self.logger = PageLogger()  # Disabled by default.
        else:
            self.logger = logger
        self.logger.enter_function()
        self.logger.info("Wrapping the base client in ChatCompletionClientRecorder.")

        self.base_client = client
        self.mode = mode
        self.session_file_path = os.path.expanduser(session_file_path)
        self.records: List[RecordDict] = []
        self._record_index = 0
        self._num_checked_records = 0
        if self.mode == "record":
            # Prepare to record the messages and responses.
            self.logger.info("Recording mode enabled.\nRecording session to: " + self.session_file_path)
        elif self.mode == "replay":
            # Load the previously recorded messages and responses from disk.
            self.logger.info("Replay mode enabled.\nRetrieving session from: " + self.session_file_path)
            try:
                with open(self.session_file_path, "r") as f:
                    self.records = json.load(f)
            except Exception as e:
                error_str = f"\nFailed to load recorded session: '{self.session_file_path}': {e}"
                self.logger.error(error_str)
                raise ValueError(error_str) from e

        self.logger.leave_function()

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        current_messages: List[Mapping[str, Any]] = [msg.model_dump() for msg in messages]
        if self.mode == "record":
            response = await self.base_client.create(
                messages,
                tools=tools,
                json_output=json_output,
                extra_create_args=extra_create_args,
                cancellation_token=cancellation_token,
            )

            rec: RecordDict = {
                "mode": "create",
                "messages": current_messages,
                "response": response.model_dump(),
                "stream": [],
            }
            self.records.append(rec)
            return response
        elif self.mode == "replay":
            if self._record_index >= len(self.records):
                error_str = "\nNo more recorded turns to check."
                self.logger.error(error_str)
                raise ValueError(error_str)
            rec = self.records[self._record_index]
            if rec.get("mode") != "create":
                error_str = f"\nRecorded call type mismatch at index {self._record_index}: expected 'create', got '{rec.get('mode')}'."
                self.logger.error(error_str)
                raise ValueError(error_str)
            recorded_messages = rec.get("messages")
            if recorded_messages != current_messages:
                error_str = (
                    "\nCurrent message list doesn't match the recorded message list. See the pagelogs for details."
                )
                assert recorded_messages is not None
                self.logger.log_dict_list(recorded_messages, "recorded message list")
                assert current_messages is not None
                self.logger.log_dict_list(current_messages, "current message list")
                self.logger.error(error_str)
                raise ValueError(error_str)
            self._record_index += 1
            self._num_checked_records += 1

            data = rec.get("response")
            # Populate a CreateResult from the data.
            assert data is not None
            result = CreateResult(
                content=data.get("content", ""),
                finish_reason=data.get("finish_reason", "stop"),
                usage=data.get("usage", RequestUsage(prompt_tokens=0, completion_tokens=0)),
                cached=True,
            )
            return result

        else:
            error_str = f"\nUnknown mode: {self.mode}"
            self.logger.error(error_str)
            raise ValueError(error_str)

    def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        return self.base_client.create_stream(
            messages,
            tools=tools,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )

    async def close(self) -> None:
        await self.base_client.close()

    def actual_usage(self) -> RequestUsage:
        # Calls base_client.actual_usage() and returns the result.
        return self.base_client.actual_usage()

    def total_usage(self) -> RequestUsage:
        # Calls base_client.total_usage() and returns the result.
        return self.base_client.total_usage()

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        # Calls base_client.count_tokens() and returns the result.
        return self.base_client.count_tokens(messages, tools=tools)

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        # Calls base_client.remaining_tokens() and returns the result.
        return self.base_client.remaining_tokens(messages, tools=tools)

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        # Calls base_client.capabilities and returns the result.
        warnings.warn("capabilities is deprecated, use model_info instead", DeprecationWarning, stacklevel=2)
        return self.base_client.capabilities

    @property
    def model_info(self) -> ModelInfo:
        # Calls base_client.model_info and returns the result.
        return self.base_client.model_info

    def finalize(self) -> None:
        """
        In record mode, saves the accumulated records to disk.
        In replay mode, makes sure all the records were checked.
        """
        self.logger.enter_function()
        if self.mode == "record":
            try:
                # Create the directory if it doesn't exist.
                os.makedirs(os.path.dirname(self.session_file_path), exist_ok=True)
                # Write the records to disk.
                with open(self.session_file_path, "w") as f:
                    json.dump(self.records, f, indent=2)
                    self.logger.info("\nRecorded session was saved to: " + self.session_file_path)
            except Exception as e:
                error_str = f"Failed to write records to '{self.session_file_path}': {e}"
                self.logger.error(error_str)
                raise ValueError(error_str) from e
        elif self.mode == "replay":
            if self._num_checked_records < len(self.records):
                error_str = f"\nEarly termination. Only {self._num_checked_records} of the {len(self.records)} recorded turns were checked."
                self.logger.error(error_str)
                raise ValueError(error_str)
            self.logger.info("\nRecorded session was fully replayed and checked.")
        self.logger.leave_function()
