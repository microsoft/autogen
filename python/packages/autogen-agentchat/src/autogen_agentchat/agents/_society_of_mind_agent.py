from typing import Any, AsyncGenerator, List, Mapping, Sequence

from autogen_core import CancellationToken, Component, ComponentModel
from autogen_core.models import ChatCompletionClient, LLMMessage, SystemMessage
from pydantic import BaseModel
from typing_extensions import Self

from autogen_agentchat.base import Response
from autogen_agentchat.state import SocietyOfMindAgentState

from ..base import TaskResult, Team
from ..messages import (
    AgentEvent,
    ChatMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
)
from ._base_chat_agent import BaseChatAgent


class SocietyOfMindAgentConfig(BaseModel):
    """The declarative configuration for a SocietyOfMindAgent."""

    name: str
    team: ComponentModel
    model_client: ComponentModel
    description: str | None = None
    instruction: str | None = None
    response_prompt: str | None = None


class SocietyOfMindAgent(BaseChatAgent, Component[SocietyOfMindAgentConfig]):
    """An agent that uses an inner team of agents to generate responses.

    Each time the agent's :meth:`on_messages` or :meth:`on_messages_stream`
    method is called, it runs the inner team of agents and then uses the
    model client to generate a response based on the inner team's messages.
    Once the response is generated, the agent resets the inner team by
    calling :meth:`Team.reset`.

    Args:
        name (str): The name of the agent.
        team (Team): The team of agents to use.
        model_client (ChatCompletionClient): The model client to use for preparing responses.
        description (str, optional): The description of the agent.
        instruction (str, optional): The instruction to use when generating a response using the inner team's messages.
            Defaults to :attr:`DEFAULT_INSTRUCTION`. It assumes the role of 'system'.
        response_prompt (str, optional): The response prompt to use when generating a response using the inner team's messages.
            Defaults to :attr:`DEFAULT_RESPONSE_PROMPT`. It assumes the role of 'system'.


    Example:

    .. code-block:: python

        import asyncio
        from autogen_agentchat.ui import Console
        from autogen_agentchat.agents import AssistantAgent, SocietyOfMindAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import TextMentionTermination


        async def main() -> None:
            model_client = OpenAIChatCompletionClient(model="gpt-4o")

            agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a writer, write well.")
            agent2 = AssistantAgent(
                "assistant2",
                model_client=model_client,
                system_message="You are an editor, provide critical feedback. Respond with 'APPROVE' if the text addresses all feedbacks.",
            )
            inner_termination = TextMentionTermination("APPROVE")
            inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination)

            society_of_mind_agent = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=model_client)

            agent3 = AssistantAgent(
                "assistant3", model_client=model_client, system_message="Translate the text to Spanish."
            )
            team = RoundRobinGroupChat([society_of_mind_agent, agent3], max_turns=2)

            stream = team.run_stream(task="Write a short story with a surprising ending.")
            await Console(stream)


        asyncio.run(main())
    """

    component_config_schema = SocietyOfMindAgentConfig
    component_provider_override = "autogen_agentchat.agents.SocietyOfMindAgent"

    DEFAULT_INSTRUCTION = "Earlier you were asked to fulfill a request. You and your team worked diligently to address that request. Here is a transcript of that conversation:"
    """str: The default instruction to use when generating a response using the
    inner team's messages. The instruction will be prepended to the inner team's
    messages when generating a response using the model. It assumes the role of
    'system'."""

    DEFAULT_RESPONSE_PROMPT = (
        "Output a standalone response to the original request, without mentioning any of the intermediate discussion."
    )
    """str: The default response prompt to use when generating a response using
    the inner team's messages. It assumes the role of 'system'."""

    DEFAULT_DESCRIPTION = "An agent that uses an inner team of agents to generate responses."
    """str: The default description for a SocietyOfMindAgent."""

    def __init__(
        self,
        name: str,
        team: Team,
        model_client: ChatCompletionClient,
        *,
        description: str = DEFAULT_DESCRIPTION,
        instruction: str = DEFAULT_INSTRUCTION,
        response_prompt: str = DEFAULT_RESPONSE_PROMPT,
    ) -> None:
        super().__init__(name=name, description=description)
        self._team = team
        self._model_client = model_client
        self._instruction = instruction
        self._response_prompt = response_prompt

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        # Call the stream method and collect the messages.
        response: Response | None = None
        async for msg in self.on_messages_stream(messages, cancellation_token):
            if isinstance(msg, Response):
                response = msg
        assert response is not None
        return response

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        # Prepare the task for the team of agents.
        task = list(messages)

        # Run the team of agents.
        result: TaskResult | None = None
        inner_messages: List[AgentEvent | ChatMessage] = []
        count = 0

        # Set asdf DEBUG

        async for inner_msg in self._team.run_stream(task=task, cancellation_token=cancellation_token):
            if isinstance(inner_msg, TaskResult):
                result = inner_msg
            else:
                count += 1
                if count <= len(task):
                    # Skip the task messages.
                    continue
                yield inner_msg
                if isinstance(inner_msg, ModelClientStreamingChunkEvent):
                    # Skip the model client streaming chunk events.
                    continue
                inner_messages.append(inner_msg)
        assert result is not None

        if len(inner_messages) == 0:
            yield Response(
                chat_message=TextMessage(source=self.name, content="No response."), inner_messages=[]
                # Response's inner_messages should be empty. Cause that mean is response to outer world.
            )
        else:
            # Generate a response using the model client.
            llm_messages: List[LLMMessage] = [SystemMessage(content=self._instruction)]
            for message in inner_messages:
                if isinstance(message, ChatMessage):
                    llm_messages.append(message.to_model_message())
            llm_messages.append(SystemMessage(content=self._response_prompt))
            completion = await self._model_client.create(messages=llm_messages, cancellation_token=cancellation_token)
            assert isinstance(completion.content, str)
            yield Response(
                chat_message=TextMessage(source=self.name, content=completion.content, models_usage=completion.usage),
                inner_messages=[],
                # Response's inner_messages should be empty. Cause that mean is response to outer world.
            )

        # Reset the team.
        await self._team.reset()

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        await self._team.reset()
        # Question : Why do not clear model context???
        # Answer : Call model_client directly.

    async def save_state(self) -> Mapping[str, Any]:
        team_state = await self._team.save_state()
        state = SocietyOfMindAgentState(inner_team_state=team_state)
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        society_of_mind_state = SocietyOfMindAgentState.model_validate(state)
        await self._team.load_state(society_of_mind_state.inner_team_state)

    def _to_config(self) -> SocietyOfMindAgentConfig:
        return SocietyOfMindAgentConfig(
            name=self.name,
            team=self._team.dump_component(),
            model_client=self._model_client.dump_component(),
            description=self.description,
            instruction=self._instruction,
            response_prompt=self._response_prompt,
        )

    @classmethod
    def _from_config(cls, config: SocietyOfMindAgentConfig) -> Self:
        model_client = ChatCompletionClient.load_component(config.model_client)
        team = Team.load_component(config.team)
        return cls(
            name=config.name,
            team=team,
            model_client=model_client,
            description=config.description or cls.DEFAULT_DESCRIPTION,
            instruction=config.instruction or cls.DEFAULT_INSTRUCTION,
            response_prompt=config.response_prompt or cls.DEFAULT_RESPONSE_PROMPT,
        )
