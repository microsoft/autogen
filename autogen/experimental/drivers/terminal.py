from aioconsole import aprint
from autogen.experimental.chat import Chat, ChatStream
from autogen.experimental.types import AssistantMessage, SystemMessage, ToolMessage, UserMessage


async def run_in_terminal(chat: ChatStream) -> str:
    while not chat.done:
        had_partial_content = False
        async for content in chat.stream_step():
            if isinstance(content, (SystemMessage, UserMessage, AssistantMessage, ToolMessage)):
                if had_partial_content:
                    await aprint()
                else:
                    await aprint(content)
            else:
                had_partial_content = True
                await aprint(content.content, end="", flush=True)

    return chat.result
