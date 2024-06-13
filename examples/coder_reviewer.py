import asyncio
from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents import ChatCompletionAgent
from agnext.chat.memory import BufferedChatMemory
from agnext.chat.patterns import GroupChatManager
from agnext.chat.types import TextMessage
from agnext.components.models import OpenAI, SystemMessage
from agnext.core import AgentRuntime


def coder_reviewer(runtime: AgentRuntime) -> None:
    coder = ChatCompletionAgent(
        name="Coder",
        description="An agent that writes code",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "You are a coder. You can write code to solve problems.\n"
                "Work with the reviewer to improve your code."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
    )
    reviewer = ChatCompletionAgent(
        name="Reviewer",
        description="An agent that reviews code",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "You are a code reviewer. You focus on correctness, efficiency and safety of the code.\n"
                "Provide reviews only.\n"
                "Output only 'APPROVE' to approve the code and end the conversation."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
    )
    _ = GroupChatManager(
        name="Manager",
        description="A manager that orchestrates a back-and-forth converation between a coder and a reviewer.",
        runtime=runtime,
        participants=[coder, reviewer],  # The order of the participants indicates the order of speaking.
        memory=BufferedChatMemory(buffer_size=10),
        termination_word="APPROVE",
        on_message_received=lambda message: print(f"{'-'*80}\n{message.source}: {message.content}"),
    )


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    coder_reviewer(runtime)
    runtime.publish_message(
        TextMessage(
            content="Write a Python script that find near-duplicate paragraphs in a directory of many text files. "
            "Output the file names, line numbers and the similarity score of the near-duplicate paragraphs. ",
            source="Human",
        )
    )
    # Start the runtime.
    while True:
        await runtime.process_next()
        await asyncio.sleep(1)


asyncio.run(main())
