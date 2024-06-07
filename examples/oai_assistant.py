"""This is an example of a chat with an OAI assistant agent.
You must have OPENAI_API_KEY set up in your environment to
run this example.
"""

from typing import Any

import openai
from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents.base import BaseChatAgent
from agnext.chat.agents.oai_assistant import OpenAIAssistantAgent
from agnext.chat.patterns.group_chat import GroupChatOutput
from agnext.chat.patterns.two_agent_chat import TwoAgentChat
from agnext.chat.types import RespondNow, TextMessage
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import AgentRuntime, CancellationToken
from openai import AsyncAssistantEventHandler
from openai.types.beta import AssistantStreamEvent
from openai.types.beta.threads import Text, TextDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from typing_extensions import override


class TwoAgentChatOutput(GroupChatOutput):  # type: ignore
    def on_message_received(self, message: Any) -> None:
        pass

    def get_output(self) -> Any:
        return None

    def reset(self) -> None:
        pass


sep = "-" * 50


class UserProxyAgent(BaseChatAgent, TypeRoutedAgent):  # type: ignore
    def __init__(self, name: str, runtime: AgentRuntime) -> None:  # type: ignore
        super().__init__(
            name=name,
            description="A human user",
            runtime=runtime,
        )

    @message_handler()  # type: ignore
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:  # type: ignore
        # TODO: render image if message has image.
        # print(f"{message.source}: {message.content}")
        pass

    @message_handler()  # type: ignore
    async def on_respond_now(self, message: RespondNow, cancellation_token: CancellationToken) -> TextMessage:  # type: ignore
        user_input = input(f"\n{sep}\nYou: ")
        # TODO: add parsing for special commands e.g., upload files, exit, etc.
        return TextMessage(content=user_input, source=self.name)


class EventHandler(AsyncAssistantEventHandler):
    @override
    async def on_event(self, event: AssistantStreamEvent) -> None:
        if event.event == "thread.run.step.created":
            details = event.data.step_details
            if details.type == "tool_calls":
                print("\nGenerating code to interpret:\n\n```python")
        elif event.event == "thread.message.created":
            print(f"{sep}\nAssistant:\n")

    @override
    async def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        print(delta.value, end="", flush=True)

    @override
    async def on_run_step_done(self, run_step: RunStep) -> None:
        details = run_step.step_details
        if details.type == "tool_calls":
            for tool in details.tool_calls:
                if tool.type == "code_interpreter":
                    print("\n```\nExecuting code...")

    @override
    async def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        details = delta.step_details
        if details is not None and details.type == "tool_calls":
            for tool in details.tool_calls or []:
                if tool.type == "code_interpreter" and tool.code_interpreter and tool.code_interpreter.input:
                    print(tool.code_interpreter.input, end="", flush=True)


def assistant_chat(runtime: AgentRuntime) -> TwoAgentChat:  # type: ignore
    user = UserProxyAgent(name="User", runtime=runtime)
    oai_assistant = openai.beta.assistants.create(
        model="gpt-4-turbo",
        description="An AI assistant that helps with everyday tasks.",
        instructions="Help the user with their task.",
        tools=[{"type": "code_interpreter"}],
    )
    thread = openai.beta.threads.create()
    assistant = OpenAIAssistantAgent(
        name="Assistant",
        description="An AI assistant that helps with everyday tasks.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=oai_assistant.id,
        thread_id=thread.id,
        assistant_event_handler_factory=lambda: EventHandler(),
    )
    return TwoAgentChat(
        name="AssistantChat",
        description="A chat with an AI assistant",
        runtime=runtime,
        initial_sender=user,
        initial_recipient=assistant,
        num_rounds=100,
        output=TwoAgentChatOutput(),
    )


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    chat = assistant_chat(runtime)
    future = runtime.send_message(
        TextMessage(content="Hello.", source="User"),
        chat,
    )
    while not future.done():
        await runtime.process_next()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
