from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.base import MessageContext, TopicId
from autogen_core.components import FunctionCall, RoutedAgent, TypeSubscription, message_handler
from autogen_agentchat.base import Response

from autogen_agentchat.messages import (
    AgentMessage,
    ChatMessage,
    TextMessage,
    HandoffMessage,
    MultiModalMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
    StopMessage
)


class UserAgent(RoutedAgent):
    def __init__(self,name:str, description: str, user_topic_type: str, agent_topic_type: str) -> None:
        super().__init__(description)
        self.name=name
        self._user_topic_type = user_topic_type
        self._agent_topic_type = agent_topic_type

    @message_handler
    async def handle_user_login(self, message: UserMessage, ctx: MessageContext) -> None:
        print(f"{'-'*80}\nUser login, session ID: {self.id.key}.", flush=True)
        # Get the user's initial input after login.
        user_input = input("开始输入你的任务内容: ")
        print(f"{'-'*80}\n{self.id.type}:\n{user_input}")
        await self.publish_message(
            UserMessage(content=user_input, source=self),
            topic_id=TopicId(self._agent_topic_type, source=self.id.key),
        )

    @message_handler
    async def handle_task_result(self, message: HandoffMessage, ctx: MessageContext) -> None:
        # Get the user's input after receiving a response from an agent.
        print(f"来自{message.source}给出的信息{message.content}", flush=True)
        user_input = input("您的输入: ")
        await self.publish_message(
            UserMessage(context=user_input,source=self.name), topic_id=TopicId(message.target, source=self.id.key)
        )