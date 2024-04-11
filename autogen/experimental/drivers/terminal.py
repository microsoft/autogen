from aioconsole import aprint  # type: ignore

from autogen.experimental.chat import ChatOrchestratorStream
from autogen.experimental.types import MessageAndSender


async def run_in_terminal(chat: ChatOrchestratorStream) -> str:
    while not chat.done:
        had_partial_content = False
        async for value in chat.stream_step():
            if isinstance(value, MessageAndSender):
                if had_partial_content:
                    await aprint()
                else:
                    await aprint(value)
            else:
                had_partial_content = True
                await aprint(value.item.content, end="", flush=True)

    return chat.result.summary
