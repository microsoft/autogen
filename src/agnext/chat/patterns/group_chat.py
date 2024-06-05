from typing import Any, List, Protocol, Sequence

from ...components import TypeRoutedAgent, message_handler
from ...core import AgentRuntime, CancellationToken
from ..agents.base import BaseChatAgent
from ..types import Reset, RespondNow, TextMessage


class GroupChatOutput(Protocol):
    def on_message_received(self, message: Any) -> None: ...

    def get_output(self) -> Any: ...

    def reset(self) -> None: ...


class GroupChat(BaseChatAgent, TypeRoutedAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        agents: Sequence[BaseChatAgent],
        num_rounds: int,
        output: GroupChatOutput,
    ) -> None:
        self._agents = agents
        self._num_rounds = num_rounds
        self._history: List[Any] = []
        self._output = output
        super().__init__(name, description, runtime)

    @property
    def subscriptions(self) -> Sequence[type]:
        agent_sublists = [agent.subscriptions for agent in self._agents]
        return [Reset, RespondNow] + [item for sublist in agent_sublists for item in sublist]

    @message_handler()
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        self._history.clear()

    @message_handler()
    async def on_respond_now(self, message: RespondNow, cancellation_token: CancellationToken) -> Any:
        return self._output.get_output()

    @message_handler()
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> Any:
        # TODO: how should we handle the group chat receiving a message while in the middle of a conversation?
        # Should this class disallow it?

        self._history.append(message)
        round = 0
        prev_speaker = None

        while round < self._num_rounds:
            # TODO: add support for advanced speaker selection.
            # Select speaker (round-robin for now).
            speaker = self._agents[round % len(self._agents)]

            # Send the last message to all agents except the previous speaker.
            for agent in [agent for agent in self._agents if agent is not prev_speaker]:
                # TODO gather and await
                _ = await self._send_message(
                    self._history[-1],
                    agent,
                    cancellation_token=cancellation_token,
                )
                # TODO handle if response is not None

            # Request the speaker to speak.
            response = await self._send_message(
                RespondNow(),
                speaker,
                cancellation_token=cancellation_token,
            )

            if response is not None:
                # Append the response to the history.
                self._history.append(response)
                self._output.on_message_received(response)

            # Increment the round.
            round += 1
            prev_speaker = speaker

        output = self._output.get_output()
        self._output.reset()
        self._history.clear()
        return output
