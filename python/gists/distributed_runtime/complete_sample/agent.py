import asyncio
from typing import Any, Iterable, List, Type

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import (
    CancellationToken,
    DefaultTopicId,
    MessageContext,
    MessageSerializer,
    RoutedAgent,
    TypeSubscription,
    message_handler,
    try_get_known_serializers_for_type,
)
from autogen_core.components.models import (
    LLMMessage,
)
from autogen_ext.models import AzureOpenAIChatCompletionClient
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

client_config = {
    "model": "gpt-4o",
    "azure_endpoint": "https://{your-custom-endpoint}.openai.azure.com",
    "azure_deployment": "{your-azure-deployment}",
    "api_version": "2024-08-01-preview",
    "azure_ad_token_provider": get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    ),
}


def get_serializers(types: Iterable[Type[Any]]) -> list[MessageSerializer[Any]]:
    serializers = []
    for type in types:
        serializers.extend(try_get_known_serializers_for_type(type))  # type: ignore
    return serializers  # type: ignore [reportUnknownVariableType]


class AssistantAgentWrapper(RoutedAgent):
    def __init__(
        self,
        description: str,
        group_chat_topic_type: str,
        agent: AssistantAgent,
    ) -> None:
        super().__init__(description=description)
        self._group_chat_topic_type = group_chat_topic_type
        self._agent = agent
        self._chat_history: List[LLMMessage] = []

    @message_handler
    async def handle_message(self, message: TextMessage, ctx: MessageContext) -> None:
        response = await self._agent.on_messages([message], CancellationToken())
        print("\n", "-" * 50, "\n", response.chat_message.content)
        if response.chat_message.content != "TERMINATE":
            await self.publish_message(
                response.chat_message,
                topic_id=DefaultTopicId(type="conversation_topic"),
            )
        else:
            print("Terminating! Won't continue!")


async def main(host_address: str, agent_name: str, agent_system_message: str):
    agent_runtime = GrpcWorkerAgentRuntime(host_address=host_address)
    agent_runtime.add_message_serializer(get_serializers([TextMessage]))  # type: ignore[arg-type]

    print(f"Starting Agent with ID: {agent_name}")

    agent_runtime.start()
    model_client = AzureOpenAIChatCompletionClient(**client_config)

    agent_type = await AssistantAgentWrapper.register(
        agent_runtime,
        agent_name,
        lambda: AssistantAgentWrapper(
            description=agent_system_message,
            group_chat_topic_type="conversation_topic",
            agent=AssistantAgent(name=agent_name, system_message=agent_system_message, model_client=model_client),
        ),
    )

    await agent_runtime.add_subscription(TypeSubscription(topic_type="conversation_topic", agent_type=agent_type.type))

    await agent_runtime.publish_message(
        TextMessage(content="Please write a short story about the gingerbread in halloween!", source="User"),
        topic_id=DefaultTopicId(type="conversation_topic"),
    )

    await agent_runtime.stop_when_signal()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Usage: python agent1.py <host_address> <agent_id>")
        sys.exit(1)
    asyncio.run(main(host_address=sys.argv[1], agent_name=sys.argv[2], agent_system_message=sys.argv[3]))
