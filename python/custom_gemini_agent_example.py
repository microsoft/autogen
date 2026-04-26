
import os
from typing import AsyncGenerator, Sequence
import asyncio
from autogen_agentchat.agents import BaseChatAgent, AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_core import CancellationToken, Component
from autogen_core.model_context import UnboundedChatCompletionContext
from autogen_core.models import AssistantMessage, RequestUsage, UserMessage
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from pydantic import BaseModel
from typing_extensions import Self

# Requires: pip install google-genai
from google import genai
from google.genai import types


# Declarative config for GeminiAssistantAgent
class GeminiAssistantAgentConfig(BaseModel):
    name: str
    description: str = "An agent that provides assistance with ability to use tools."
    model: str = "gemini-1.5-flash-002"
    system_message: str | None = None


class GeminiAssistantAgent(BaseChatAgent, Component[GeminiAssistantAgentConfig]):  # type: ignore[no-redef]
    component_config_schema = GeminiAssistantAgentConfig
    # component_provider_override = "mypackage.agents.GeminiAssistantAgent"

    def __init__(
        self,
        name: str,
        description: str = "An agent that provides assistance with ability to use tools.",
        model: str = "gemini-1.5-flash-002",
        api_key: str = os.environ.get("GEMINI_API_KEY", ""),
        system_message: str
        | None = "You are a helpful assistant that can respond to messages. Reply with TERMINATE when the task has been completed.",
    ):
        super().__init__(name=name, description=description)
        self._model_context = UnboundedChatCompletionContext()
        self._model_client = genai.Client(api_key=api_key)
        self._system_message = system_message
        self._model = model

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        final_response = None
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                final_response = message
        if final_response is None:
            raise AssertionError("The stream should have returned the final result.")
        return final_response

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        # Add messages to the model context
        for msg in messages:
            await self._model_context.add_message(msg.to_model_message())
        # Get conversation history
        history = [
            (msg.source if hasattr(msg, "source") else "system")
            + ": "
            + (msg.content if isinstance(msg.content, str) else "")
            + "\n"
            for msg in await self._model_context.get_messages()
        ]
        # Generate response using Gemini
        response = self._model_client.models.generate_content(
            model=self._model,
            contents=f"History: {history}\nGiven the history, please provide a response",
            config=types.GenerateContentConfig(
                system_instruction=self._system_message,
                temperature=0.3,
            ),
        )
        # Create usage metadata
        usage = RequestUsage(
            prompt_tokens=response.usage_metadata.prompt_token_count,
            completion_tokens=response.usage_metadata.candidates_token_count,
        )
        # Add response to model context
        await self._model_context.add_message(AssistantMessage(content=response.text, source=self.name))
        # Yield the final response
        yield Response(
            chat_message=TextMessage(content=response.text, source=self.name, models_usage=usage),
            inner_messages=[],
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        await self._model_context.clear()

    @classmethod
    def _from_config(cls, config: GeminiAssistantAgentConfig) -> Self:
        return cls(
            name=config.name, description=config.description, model=config.model, system_message=config.system_message
        )

    def _to_config(self) -> GeminiAssistantAgentConfig:
        return GeminiAssistantAgentConfig(
            name=self.name,
            description=self.description,
            model=self._model,
            system_message=self._system_message,
        )


# Example: Dumping and loading the agent declaratively
def run_gemini_agent_example():
    gemini_assistant = GeminiAssistantAgent("gemini_assistant")
    config = gemini_assistant.dump_component()
    print(config.model_dump_json(indent=2))
    loaded_agent = GeminiAssistantAgent.load_component(config)
    print(loaded_agent)
    return Console(gemini_assistant.run_stream(task="What is the capital of New York?"))

async def run_team_with_gemini_critic():
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    primary_agent = AssistantAgent(
        "primary",
        model_client=model_client,
        system_message="You are a helpful AI assistant.",
    )
    gemini_critic_agent = GeminiAssistantAgent(
        "gemini_critic",
        system_message="Provide constructive feedback. Respond with 'APPROVE' to when your feedbacks are addressed.",
    )
    termination = TextMentionTermination("APPROVE") | MaxMessageTermination(10)
    team = RoundRobinGroupChat([primary_agent, gemini_critic_agent], termination_condition=termination)
    await Console(team.run_stream(task="Write a Haiku poem with 4 lines about the fall season."))
    await model_client.close()

if __name__ == "__main__":
    # To run the Gemini agent alone and see config dump/load:
    # asyncio.run(run_gemini_agent_example())
    # To run the team with Gemini critic:
    asyncio.run(run_team_with_gemini_critic())
