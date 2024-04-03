from aioconsole import aprint
from autogen.experimental.chat import Chat


async def run_in_terminal(chat: Chat) -> str:
    while not chat.done:
        step = await chat.step()
        await aprint(step)

    return chat.result
