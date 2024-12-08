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
from autogen_ext.models import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def get_azure_openai_model_client(azure_openai_endpoint: str, azure_openai_deployment: str):
    client_config = {
        "model": "gpt-4o",
        "azure_endpoint": azure_openai_endpoint,
        "azure_deployment": azure_openai_deployment,
        "api_version": "2024-08-01-preview",
        "azure_ad_token_provider": get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        ),
    }

    return AzureOpenAIChatCompletionClient(**client_config)


def get_openai_model_client(api_key: str):
    return OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)


def get_model_client(openai_api_key: str, azure_openai_endpoint: str, azure_openai_deployment: str):
    if azure_openai_endpoint and azure_openai_deployment:
        return get_azure_openai_model_client(azure_openai_endpoint, azure_openai_deployment)
    elif openai_api_key:
        return get_openai_model_client(openai_api_key)
    else:
        raise ValueError(
            "---> None of (AZURE_OPENAI_ENDPOINT,AZURE_OPENAI_DEPLOYMENT) or OPENAI_API_KEY variables are found. Please set them "
        )


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
            await asyncio.sleep(1)
        else:
            print("Terminating! Won't continue!")


async def main(
    host_address: str,
    agent_name: str,
    agent_system_message: str,
    openai_api_key: str,
    azure_openai_endpoint: str,
    azure_openai_deployment: str,
):
    agent_runtime = GrpcWorkerAgentRuntime(host_address=host_address)
    agent_runtime.add_message_serializer(get_serializers([TextMessage]))  # type: ignore[arg-type]

    print(f"Starting Agent with ID: {agent_name}")

    agent_runtime.start()

    agent_type = await AssistantAgentWrapper.register(
        agent_runtime,
        agent_name,
        lambda: AssistantAgentWrapper(
            description=agent_system_message,
            group_chat_topic_type="conversation_topic",
            agent=AssistantAgent(
                name=agent_name,
                system_message=agent_system_message,
                model_client=get_model_client(openai_api_key, azure_openai_endpoint, azure_openai_deployment),
            ),
        ),
    )

    await agent_runtime.add_subscription(TypeSubscription(topic_type="conversation_topic", agent_type=agent_type.type))

    if agent_name == "editor_agent":
        await agent_runtime.publish_message(
            TextMessage(
                content="Please write a short story about the gingerbread in halloween!", source="editor_agent"
            ),
            topic_id=DefaultTopicId(type="conversation_topic"),
        )
        await asyncio.sleep(1)

    await agent_runtime.stop_when_signal()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the agent with specified parameters.")
    parser.add_argument(
        "--host-address", type=str, help="The address of the host to connect to.", default="localhost:5000"
    )
    parser.add_argument("--agent-name", type=str, help="The name of the agent.", required=True)
    parser.add_argument("--agent-system-message", type=str, help="The system message for the agent.", required=True)
    parser.add_argument("--openai-api-key", type=str, help="The OpenAI API key.", default="")
    parser.add_argument(
        "--azure-openai-endpoint",
        type=str,
        help="The Azure OpenAI endpoint. Example: https://{your-custom-endpoint}.openai.azure.com",
        default="",
    )
    parser.add_argument("--azure-openai-deployment", type=str, help="The Azure OpenAI deployment.", default="")
    args = parser.parse_args()

    asyncio.run(
        main(
            host_address=args.host_address,
            agent_name=args.agent_name,
            agent_system_message=args.agent_system_message,
            openai_api_key=args.openai_api_key,
            azure_openai_endpoint=args.azure_openai_endpoint,
            azure_openai_deployment=args.azure_openai_deployment,
        )
    )
