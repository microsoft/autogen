import asyncio
import os

from autogen.experimental import AssistantAgent, OpenAI, TwoAgentChat
from autogen.experimental.drivers.legacy_terminal import legacy_run_in_terminal
from autogen.experimental.terminations import ReflectionTerminationManager


async def main() -> None:

    model_client = OpenAI(model="gpt-4-0125-preview", api_key=os.environ["OPENAI_API_KEY"])

    json_model_client = OpenAI(
        model="gpt-4-0125-preview", api_key=os.environ["OPENAI_API_KEY"], response_format={"type": "json_object"}
    )

    bob = AssistantAgent(
        name="bob", system_message="You are a comedian named bob, who can create any joke.", model_client=model_client
    )
    alice = AssistantAgent(
        name="alice",
        system_message="You are a member of the audience named alice, interested in knock knock jokes.",
        model_client=model_client,
    )
    chat = TwoAgentChat(
        alice,
        bob,
        termination_manager=ReflectionTerminationManager(
            model_client=json_model_client, goal="A knock knock joke has been produced."
        ),
    )

    # BUG: improve syntax so that its clear who starts the chat
    await legacy_run_in_terminal(chat)

    print("--Chat Terminated--")
    print(chat.termination_result)

    print("--Chat History--")
    # print(chat.chat_history.messages)
    for msg in chat.chat_history.messages:
        print(msg)


if __name__ == "__main__":
    asyncio.run(main())
