from aioconsole import aprint  # type: ignore

from autogen.experimental.chat import ChatOrchestratorStream
from autogen.experimental.types import IntermediateResponse


async def run_in_terminal(chat: ChatOrchestratorStream) -> str:
    while not chat.done:
        had_partial_content = False
        async for value in chat.stream_step():
            if isinstance(value, IntermediateResponse):
                had_partial_content = True
                await aprint(value.item.content, end="", flush=True)
            else:
                if had_partial_content:
                    await aprint()
                else:
                    await aprint(value)

    return chat.result.summary
