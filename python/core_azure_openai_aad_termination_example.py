"""
Azure OpenAI with AAD Auth & Termination/Intervention Handler Example

This example demonstrates:
- Using Azure OpenAI with Azure Active Directory (AAD) authentication
- Termination detection using an intervention handler

Requirements:
- pip install azure-identity autogen-core autogen-ext
- Assign Cognitive Services OpenAI User role to your AAD identity

Run with: python python/core_azure_openai_aad_termination_example.py
"""
import asyncio
from dataclasses import dataclass
from typing import Any

from autogen_core import (
    DefaultInterventionHandler,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    default_subscription,
    message_handler,
)
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# ------------------- Message Protocol -------------------
@dataclass
class Message:
    content: Any

@dataclass
class Termination:
    reason: str

# ------------------- Agent Example -------------------
@default_subscription
class AnAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("MyAgent")
        self.received = 0

    @message_handler
    async def on_new_message(self, message: Message, ctx: MessageContext) -> None:
        self.received += 1
        print(f"Received message {self.received}: {message.content}")
        if self.received > 3:
            await self.publish_message(Termination(reason="Reached maximum number of messages"), DefaultTopicId())

# ------------------- Termination Handler -------------------
class TerminationHandler(DefaultInterventionHandler):
    def __init__(self) -> None:
        self._termination_value: Termination | None = None

    async def on_publish(self, message: Any, *, message_context: MessageContext) -> Any:
        if isinstance(message, Termination):
            self._termination_value = message
        return message

    @property
    def termination_value(self) -> Termination | None:
        return self._termination_value

    @property
    def has_terminated(self) -> bool:
        return self._termination_value is not None

# ------------------- Azure OpenAI Client Setup -------------------
def create_azure_openai_client():
    # Replace these with your Azure OpenAI deployment details
    azure_deployment = "{your-azure-deployment}"
    model = "{model-name, such as gpt-4o}"
    api_version = "2024-02-01"
    azure_endpoint = "https://{your-custom-endpoint}.openai.azure.com/"
    # Create the token provider
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    client = AzureOpenAIChatCompletionClient(
        azure_deployment=azure_deployment,
        model=model,
        api_version=api_version,
        azure_endpoint=azure_endpoint,
        azure_ad_token_provider=token_provider,
    )
    return client

# ------------------- Main Example -------------------
async def main():
    # Uncomment to use Azure OpenAI client in your agents
    # model_client = create_azure_openai_client()

    termination_handler = TerminationHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[termination_handler])
    await AnAgent.register(runtime, "my_agent", AnAgent)
    runtime.start()
    # Publish more than 3 messages to trigger termination
    for i in range(4):
        await runtime.publish_message(Message(f"hello {i+1}"), DefaultTopicId())
    # Wait for termination
    await runtime.stop_when(lambda: termination_handler.has_terminated)
    print(termination_handler.termination_value)

if __name__ == "__main__":
    asyncio.run(main())
