from typing import AsyncGenerator, List, Sequence

from autogen_core import CancellationToken, Image
from autogen_core.models import ChatCompletionClient
from autogen_core.models._types import SystemMessage

from autogen_agentchat.base import Response

from ..base import TaskResult, Team
from ..messages import (
    AgentMessage,
    ChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
)
from ._base_chat_agent import BaseChatAgent


class SocietyOfMindAgent(BaseChatAgent):
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


    Example:

    .. code-block:: python

        import asyncio
        from autogen_agentchat.agents import AssistantAgent, SocietyOfMindAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import MaxMessageTermination


        async def main() -> None:
            model_client = OpenAIChatCompletionClient(model="gpt-4o")

            agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a helpful assistant.")
            agent2 = AssistantAgent("assistant2", model_client=model_client, system_message="You are a helpful assistant.")
            inner_termination = MaxMessageTermination(3)
            inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination)

            society_of_mind_agent = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=model_client)

            agent3 = AssistantAgent("assistant3", model_client=model_client, system_message="You are a helpful assistant.")
            agent4 = AssistantAgent("assistant4", model_client=model_client, system_message="You are a helpful assistant.")
            outter_termination = MaxMessageTermination(10)
            team = RoundRobinGroupChat([society_of_mind_agent, agent3, agent4], termination_condition=outter_termination)

            stream = team.run_stream(task="Tell me a one-liner joke.")
            async for message in stream:
                print(message)


        asyncio.run(main())
    """

    def __init__(
        self,
        name: str,
        team: Team,
        model_client: ChatCompletionClient,
        *,
        description: str = "An agent that uses an inner team of agents to generate responses.",
        task_prompt: str = "{transcript}\nContinue.",
        response_prompt: str = "Here is a transcript of conversation so far:\n{transcript}\n\\Provide a response to the original request.",
    ) -> None:
        super().__init__(name=name, description=description)
        self._team = team
        self._model_client = model_client
        if "{transcript}" not in task_prompt:
            raise ValueError("The task prompt must contain the '{transcript}' placeholder for the transcript.")
        self._task_prompt = task_prompt
        if "{transcript}" not in response_prompt:
            raise ValueError("The response prompt must contain the '{transcript}' placeholder for the transcript.")
        self._response_prompt = response_prompt

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage]

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
    ) -> AsyncGenerator[AgentMessage | Response, None]:
        # Build the context.
        delta = list(messages)
        task: str | None = None
        if len(delta) > 0:
            task = self._task_prompt.format(transcript=self._create_transcript(delta))

        # Run the team of agents.
        result: TaskResult | None = None
        inner_messages: List[AgentMessage] = []
        async for inner_msg in self._team.run_stream(task=task, cancellation_token=cancellation_token):
            if isinstance(inner_msg, TaskResult):
                result = inner_msg
            else:
                yield inner_msg
                inner_messages.append(inner_msg)
        assert result is not None

        if len(inner_messages) < 2:
            # The first message is the task message so we need at least 2 messages.
            yield Response(
                chat_message=TextMessage(source=self.name, content="No response."), inner_messages=inner_messages
            )
        else:
            prompt = self._response_prompt.format(transcript=self._create_transcript(inner_messages[1:]))
            completion = await self._model_client.create(
                messages=[SystemMessage(content=prompt)], cancellation_token=cancellation_token
            )
            assert isinstance(completion.content, str)
            yield Response(
                chat_message=TextMessage(source=self.name, content=completion.content, models_usage=completion.usage),
                inner_messages=inner_messages,
            )

        # Reset the team.
        await self._team.reset()

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        await self._team.reset()

    def _create_transcript(self, messages: Sequence[AgentMessage]) -> str:
        transcript = ""
        for message in messages:
            if isinstance(message, TextMessage | StopMessage | HandoffMessage):
                transcript += f"{message.source}: {message.content}\n"
            elif isinstance(message, MultiModalMessage):
                for content in message.content:
                    if isinstance(content, Image):
                        transcript += f"{message.source}: [Image]\n"
                    else:
                        transcript += f"{message.source}: {content}\n"
            else:
                raise ValueError(f"Unexpected message type: {message} in {self.__class__.__name__}")
        return transcript
