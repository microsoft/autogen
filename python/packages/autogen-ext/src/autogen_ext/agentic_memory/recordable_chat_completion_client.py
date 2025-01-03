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


class RecordableChatCompletionClient:
    """
    Wraps a client object to record messages and responses (in record mode)
    or check the messages and replay the responses (in check-replay mode).
    """
    def __init__(self, base_client: AzureOpenAIChatCompletionClient, mode: str, page_log: PageLog) -> None:
        self.base_client = base_client
        self.mode = mode
        self.path_to_output_file = os.path.join(os.path.expanduser("~/sessions/"), "session.json")
        if page_log is not None:
            page_log.append_entry_line("Wrapped the base client in a RecordableChatCompletionClient.")
        if self.mode == "record":
            # Prepare to record the messages and responses.
            page_log.append_entry_line("Recording mode enabled.")
            self.recorded_turns = []
        elif self.mode == "check-replay":
            # Load the recorded messages and responses from disk.
            page_log.append_entry_line("Replay-check mode enabled.")
            self.recorded_turns = self.load()
            self.next_turn = 0

    async def create(
            self,
            messages: Sequence[LLMMessage],
            tools: Sequence[Tool | ToolSchema] = [],
            json_output: Optional[bool] = None,
            extra_create_args: Mapping[str, Any] = {},
            cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        if self.mode == "pass-through":
            return await self.base_client.create(messages, tools, json_output, extra_create_args, cancellation_token)
        elif self.mode == "record":
            response = await self.base_client.create(messages, tools, json_output, extra_create_args, cancellation_token)
            self.record(messages, response)
            return response
        elif self.mode == "check-replay":
            recorded_response = self.replay_and_check(messages)
            return recorded_response
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

    def convert_messages(self, messages: Sequence[LLMMessage]) -> List[Dict[str, str]]:
        converted_messages = []
        for message in messages:
            turn = {"content": message.content, "source": 'System' if message.type == "SystemMessage" else message.source}
            converted_messages.append(turn)
        return converted_messages

    def record(self, messages: Sequence[LLMMessage], response: CreateResult) -> None:
        # Record the messages and response.
        converted_messages = self.convert_messages(messages)
        turn = {"messages": converted_messages, "response": response.content}
        self.recorded_turns.append(turn)

    def replay_and_check(self, messages):
        # Compare the messages to the recorded messages, and return the recorded response.
        assert self.next_turn < len(self.recorded_turns)
        recorded_turn = self.recorded_turns[self.next_turn]
        self.next_turn += 1
        recorded_messages = recorded_turn["messages"]
        converted_messages = self.convert_messages(messages)
        assert converted_messages == recorded_messages
        response = recorded_turn["response"]
        cur_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        result = CreateResult(finish_reason="stop", content=response, usage=cur_usage, cached=True)
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
