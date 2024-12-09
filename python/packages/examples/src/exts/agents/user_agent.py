from typing import AsyncGenerator, List, Sequence

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import AgentMessage, ChatMessage, TextMessage,HandoffMessage
from autogen_core.base import CancellationToken
import asyncio
from typing import List, Sequence

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage
from autogen_core.base import CancellationToken

class UserProxyAgent(BaseChatAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name, "A human user.")

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage,HandoffMessage]

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        request = messages[-1]
        print(f"来自{request.source}的回复： {request.content}\n")
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, "Enter your response: ")

        

        if isinstance(request,HandoffMessage):
            return Response(chat_message=HandoffMessage(content=user_input,target=request.source,source = self.name))

        else:
            return Response(chat_message=TextMessage(content=user_input, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


async def run_user_proxy_agent() -> None:
    user_proxy_agent = UserProxyAgent(name="user_proxy_agent")
    response = await user_proxy_agent.on_messages([], CancellationToken())
    print(response.chat_message.content)
