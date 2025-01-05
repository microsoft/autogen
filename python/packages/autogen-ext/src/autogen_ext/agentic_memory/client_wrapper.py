import os
import json
from typing import Any, List, Dict, Mapping, Optional, Sequence
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_core import CancellationToken
from autogen_core.models import (
    CreateResult,
    LLMMessage,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.agentic_memory import PageLog


class ClientWrapper:
    """
    Wraps a client object to record messages and responses (in record mode)
    or check the messages and replay the responses (in check-replay mode).
    """
    def __init__(self, base_client: AzureOpenAIChatCompletionClient, mode: str, session_name: str, page_log: PageLog) -> None:
        page = page_log.begin_page(
            summary="ClientWrapper.__init__",
            details='',
            method_call="ClientWrapper.__init__")

        self.base_client = base_client
        self.mode = mode
        self.page_log = page_log
        self.path_to_output_file = os.path.join(os.path.expanduser("~/sessions/"), session_name + ".json")
        if page_log is not None:
            page.add_lines("Wrapping the base client in a ClientWrapper.")
        if self.mode == "record":
            # Prepare to record the messages and responses.
            page.add_lines("Recording mode enabled.\nRecording session to: " + self.path_to_output_file)
            self.recorded_turns = []
        elif self.mode == "check-replay":
            # Load the recorded messages and responses from disk.
            page.add_lines("Check-Replay mode enabled.\nRetrieving session from: " + self.path_to_output_file)
            self.recorded_turns = self.load()
            self.next_turn = 0

        self.page_log.finish_page(page)

    async def create(
            self,
            messages: Sequence[LLMMessage],
            tools: Sequence[Tool | ToolSchema] = [],
            json_output: Optional[bool] = None,
            extra_create_args: Mapping[str, Any] = {},
            cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        page = self.page_log.begin_page(
            summary="ClientWrapper.create",
            details='',
            method_call="ClientWrapper.create")

        response = None

        if self.mode == "pass-through":
            page.add_lines("Passing through to the base client.")
            response = await self.base_client.create(messages, tools, json_output, extra_create_args, cancellation_token)
        elif self.mode == "record":
            page.add_lines("Recording the messages and response.")
            response = await self.base_client.create(messages, tools, json_output, extra_create_args, cancellation_token)
            self.record_one_turn(messages, response)
        elif self.mode == "check-replay":
            page.add_lines("Comparing the messages to the recorded messages.")
            response = self.check_and_replay_one_turn(messages)
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

        self.page_log.finish_page(page)
        return response

    def convert_messages(self, messages: Sequence[LLMMessage]) -> List[Dict[str, str]]:
        converted_messages = []
        for message in messages:
            turn = {"content": message.content, "source": 'System' if message.type == "SystemMessage" else message.source}
            converted_messages.append(turn)
        return converted_messages

    def record_one_turn(self, messages: Sequence[LLMMessage], response: CreateResult) -> None:
        # Record the messages and response.
        page = self.page_log.begin_page(
            summary="ClientWrapper.record_one_turn",
            details='',
            method_call="ClientWrapper.record_one_turn")

        converted_messages = self.convert_messages(messages)
        turn = {"messages": converted_messages, "response": response.content}
        self.recorded_turns.append(turn)
        self.page_log.finish_page(page)

    def check_and_replay_one_turn(self, messages):
        # Compare the messages to the recorded messages, and return the recorded response.
        page = self.page_log.begin_page(
            summary="ClientWrapper.check_and_replay_one_turn",
            details='',
            method_call="ClientWrapper.check_and_replay_one_turn")

        # Get the next recorded turn.
        assert self.next_turn < len(self.recorded_turns)
        recorded_turn = self.recorded_turns[self.next_turn]
        self.next_turn += 1

        # Check the current message list against the recorded message list.
        recorded_messages = recorded_turn["messages"]
        current_messages = self.convert_messages(messages)
        if current_messages != recorded_messages:
            error_str = "Current message list doesn't match the recorded message list."
            page.add_lines(error_str)
            page.page_log.add_message_content(recorded_messages, "recorded message list")
            page.page_log.add_message_content(current_messages, "current message list")
            self.page_log.append_exit_line(error_str)
            self.page_log.flush(final=True)  # Finalize the page log
            self.page_log.finish_page(page)
            raise ValueError(error_str)
        assert current_messages == recorded_messages

        # Return the recorded response.
        cur_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        result = CreateResult(finish_reason="stop", content=recorded_turn["response"], usage=cur_usage, cached=True)
        self.page_log.finish_page(page)
        return result

    def save(self) -> None:
        # Save the recorded messages and responses to disk.
        session = {"turns": self.recorded_turns}
        with open(self.path_to_output_file, "w", encoding="utf-8") as file:
            json.dump(session, file, ensure_ascii=False, indent=4, sort_keys=True)

    def load(self):
        # Load the recorded messages and responses from disk.
        recorded_turns = []
        with open(self.path_to_output_file, "r", encoding="utf-8") as file:
            session = json.load(file)
            recorded_turns = session["turns"]
        return recorded_turns
