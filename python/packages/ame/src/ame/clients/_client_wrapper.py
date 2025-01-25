import os
from typing import Any, Dict, List, Mapping, Optional, Sequence

import yaml
from autogen_core import CancellationToken
from autogen_core.models import (
    CreateResult,
    LLMMessage,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.agentic_memory import PageLogger
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient


class ClientWrapper:
    """
    Wraps a client object to record messages and responses (in record mode)
    or check the messages and replay the responses (in check-replay mode).
    """

    def __init__(
        self, base_client: AzureOpenAIChatCompletionClient, mode: str, session_name: str, logger: PageLogger
    ) -> None:
        self.logger = logger
        self.logger.enter_function()

        self.base_client = base_client
        self.mode = mode
        self.next_item_index = 0
        self.model_info = {"family": self.base_client.model_info["family"]}
        self.path_to_output_file = os.path.join(os.path.expanduser("~/sessions/"), session_name + ".yaml")
        self.logger.info("Wrapping the base client in a ClientWrapper.")
        if self.mode == "record":
            # Prepare to record the messages and responses.
            self.logger.info("Recording mode enabled.\nRecording session to: " + self.path_to_output_file)
            self.recorded_items = []
        elif self.mode == "check-replay":
            # Load the recorded messages and responses from disk.
            self.logger.info("Check-Replay mode enabled.\nRetrieving session from: " + self.path_to_output_file)
            self.recorded_items = self.load()

        self.logger.leave_function()

    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        response = None

        if self.mode == "pass-through":
            response = await self.base_client.create(
                messages, tools, json_output, extra_create_args, cancellation_token
            )
        elif self.mode == "record":
            response = await self.base_client.create(
                messages, tools, json_output, extra_create_args, cancellation_token
            )
            self.record_one_turn(messages, response)
        elif self.mode == "check-replay":
            response = self.check_and_replay_one_turn(messages)
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

        return response

    def convert_messages(self, messages: Sequence[LLMMessage]) -> List[Dict[str, str]]:
        converted_messages = []
        for message in messages:
            turn = {
                "content": message.content,
                "source": "System" if message.type == "SystemMessage" else message.source,
            }
            converted_messages.append(turn)
        return converted_messages

    def record_one_turn(self, messages: Sequence[LLMMessage], response: CreateResult) -> None:
        # Record the messages and response.
        converted_messages = self.convert_messages(messages)
        turn = {"messages": converted_messages, "response": response.content}
        self.recorded_items.append(turn)
        self.next_item_index += 1

    def check_and_replay_one_turn(self, messages):
        # Compare the messages to the recorded messages, and return the recorded response.
        # Get the next recorded turn.
        if self.next_item_index >= len(self.recorded_items):
            error_str = "\nNo more recorded items to check."
            self.logger.error(error_str)
            raise ValueError(error_str)
        recorded_turn = self.recorded_items[self.next_item_index]
        self.next_item_index += 1

        # Check the current message list against the recorded message list.
        if "messages" not in recorded_turn:
            error_str = "\nRecorded turn doesn't contain a messages field. Perhaps a result was recorded instead."
            self.logger.error(error_str)
            raise ValueError(error_str)
        recorded_messages = recorded_turn["messages"]
        current_messages = self.convert_messages(messages)
        if current_messages != recorded_messages:
            error_str = "\nCurrent message list doesn't match the recorded message list."
            self.logger.log_message_content(recorded_messages, "recorded message list")
            self.logger.log_message_content(current_messages, "current message list")
            self.logger.error(error_str)
            raise ValueError(error_str)
        assert current_messages == recorded_messages

        # Return the recorded response.
        cur_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        result = CreateResult(finish_reason="stop", content=recorded_turn["response"], usage=cur_usage, cached=True)
        return result

    def report_result(self, result: Any) -> None:
        if self.mode == "pass-through":
            return
        elif self.mode == "record":
            self.record_result(result)
        elif self.mode == "check-replay":
            self.check_result(result)

    def record_result(self, result: Any) -> None:
        # Record a result.
        self.recorded_items.append({"result": result})
        self.next_item_index += 1

    def check_result(self, result: Any) -> None:
        # Check a result.
        if self.next_item_index >= len(self.recorded_items):
            error_str = "\nNo more recorded items to check."
            self.logger.error(error_str)
            raise ValueError(error_str)
        recorded_result = self.recorded_items[self.next_item_index]
        self.next_item_index += 1

        if "result" not in recorded_result:
            error_str = "\nRecorded turn doesn't contain a result field. Perhaps a turn was recorded instead."
            self.logger.error(error_str)
            raise ValueError(error_str)
        if result != recorded_result["result"]:
            error_str = "\nRecorded result ({}) doesn't match the current result ({}).".format(
                recorded_result["result"], result
            )
            self.logger.error(error_str)
            raise ValueError(error_str)

    def finalize(self) -> None:
        self.logger.enter_function()
        self.report_result("Total items = " + str(self.next_item_index))
        if self.mode == "record":
            self.save()
            self.logger.error("\nRecorded session was saved to: " + self.path_to_output_file)
        elif self.mode == "check-replay":
            self.logger.error("\nRecorded session was fully replayed and checked.")
        self.logger.leave_function()

    def save(self) -> None:
        # Save the recorded messages and responses to disk.
        session = {"turns_and_results": self.recorded_items}
        with open(self.path_to_output_file, "w", encoding="utf-8") as file:
            yaml.dump(session, file, sort_keys=False)

    def load(self):
        # Load the recorded messages and responses from disk.
        recorded_turns = []
        with open(self.path_to_output_file, "r", encoding="utf-8") as file:
            session = yaml.load(file, Loader=yaml.FullLoader)
            recorded_turns = session["turns_and_results"]
        return recorded_turns
