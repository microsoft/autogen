import argparse
import asyncio

import openai
from agnext.agent_components.models_clients.openai_client import OpenAI
from agnext.chat.agents.oai_assistant import OpenAIAssistantAgent
from agnext.chat.messages import ChatMessage
from agnext.chat.patterns.group_chat import GroupChat
from agnext.chat.patterns.orchestrator import Orchestrator
from agnext.chat.runtimes import SingleThreadedRuntime


async def group_chat() -> None:
    runtime = SingleThreadedRuntime()

    joe_oai_assistant = openai.beta.assistants.create(
        model="gpt-3.5-turbo",
        name="Joe",
        instructions="You are a commedian named Joe. Make the audience laugh.",
    )
    joe_oai_thread = openai.beta.threads.create()
    joe = OpenAIAssistantAgent(
        name="Joe",
        description="Joe the commedian.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=joe_oai_assistant.id,
        thread_id=joe_oai_thread.id,
    )

    cathy_oai_assistant = openai.beta.assistants.create(
        model="gpt-3.5-turbo",
        name="Cathy",
        instructions="You are a poet named Cathy. Write beautiful poems.",
    )
    cathy_oai_thread = openai.beta.threads.create()
    cathy = OpenAIAssistantAgent(
        name="Cathy",
        description="Cathy the poet.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=cathy_oai_assistant.id,
        thread_id=cathy_oai_thread.id,
    )

    chat = GroupChat(
        "chat_room",
        "A round-robin chat room.",
        runtime,
        [joe, cathy],
        num_rounds=5,
    )

    response = runtime.send_message(ChatMessage(body="Run a show!", sender="external"), chat)

    while not response.done():
        await runtime.process_next()

    print((await response).body)


async def orchestrator() -> None:
    runtime = SingleThreadedRuntime()

    developer_oai_assistant = openai.beta.assistants.create(
        model="gpt-3.5-turbo",
        name="Developer",
        instructions="You are a Python developer.",
    )
    developer_oai_thread = openai.beta.threads.create()
    developer = OpenAIAssistantAgent(
        name="Developer",
        description="A developer that writes code.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=developer_oai_assistant.id,
        thread_id=developer_oai_thread.id,
    )

    product_manager_oai_assistant = openai.beta.assistants.create(
        model="gpt-3.5-turbo",
        name="ProductManager",
        instructions="You are a product manager good at translating customer needs into software specifications.",
    )
    product_manager_oai_thread = openai.beta.threads.create()
    product_manager = OpenAIAssistantAgent(
        name="ProductManager",
        description="A product manager that plans and comes up with specs.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=product_manager_oai_assistant.id,
        thread_id=product_manager_oai_thread.id,
    )

    chat = Orchestrator(
        "Team",
        "A software development team.",
        runtime,
        [developer, product_manager],
        model_client=OpenAI(model="gpt-3.5-turbo"),
    )

    response = runtime.send_message(
        ChatMessage(
            body="Write a simple FastAPI webapp for showing the current time.",
            sender="customer",
        ),
        chat,
    )

    while not response.done():
        await runtime.process_next()

    print((await response).body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a pattern demo.")
    chocies = ["group_chat", "orchestrator"]
    parser.add_argument(
        "--pattern",
        choices=chocies,
        help="The pattern to demo.",
    )
    args = parser.parse_args()

    if args.pattern == "group_chat":
        asyncio.run(group_chat())
    elif args.pattern == "orchestrator":
        asyncio.run(orchestrator())
    else:
        raise ValueError(f"Invalid pattern: {args.pattern}")
