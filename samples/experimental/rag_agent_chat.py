import asyncio
import os

import aioconsole

from autogen.experimental import OpenAI, TwoAgentChat
from autogen.experimental.agents.rag_agent import RAGAgent
from autogen.experimental.agents.user_input_agent import UserInputAgent
from autogen.experimental.drivers.legacy_terminal import legacy_run_in_terminal


async def user_input(prompt: str) -> str:
    res = await aioconsole.ainput(prompt)  # type: ignore
    if not isinstance(res, str):
        raise ValueError("Expected a string")
    return res


async def main() -> None:

    model_client = OpenAI(model="gpt-4-0125-preview", api_key=os.environ["OPENAI_API_KEY"])

    rag_agent = RAGAgent(
        name="RAGAgent",
        description="Simple RAG agent that can answer questions",
        data_dir=os.path.join(os.getcwd(), "data"),
        model_client=model_client,
    )
    user = UserInputAgent(
        name="User", description="Simple user that can ask questions", human_input_callback=user_input
    )
    chat = TwoAgentChat(
        user,
        rag_agent,
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
