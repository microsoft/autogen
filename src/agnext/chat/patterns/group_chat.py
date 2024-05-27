from typing import Any, List, Protocol, Sequence

from agnext.chat.types import Reset, RespondNow

from ...core import AgentRuntime, CancellationToken
from ..agents.base import BaseChatAgent


class Output(Protocol):
    def on_message_received(self, message: Any) -> None: ...

    def get_output(self) -> Any: ...

    def reset(self) -> None: ...


class GroupChat(BaseChatAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        agents: Sequence[BaseChatAgent],
        num_rounds: int,
        output: Output,
    ) -> None:
        super().__init__(name, description, runtime)
        self._agents = agents
        self._num_rounds = num_rounds
        self._history: List[Any] = []
        self._output = output

    @property
    def subscriptions(self) -> Sequence[type]:
        agent_sublists = [agent.subscriptions for agent in self._agents]
        return [Reset, RespondNow] + [item for sublist in agent_sublists for item in sublist]

    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any | None:
        if isinstance(message, Reset):
            # Reset the history.
            self._history = []
            # TODO: reset sub-agents?

        if isinstance(message, RespondNow):
            # TODO reset...
            return self._output.get_output()

        # TODO: how should we handle the group chat receiving a message while in the middle of a conversation?
        # Should this class disallow it?

        self._history.append(message)
        round = 0

        while round < self._num_rounds:
            # TODO: add support for advanced speaker selection.
            # Select speaker (round-robin for now).
            speaker = self._agents[round % len(self._agents)]

            # Send the last message to all agents.
            for agent in [agent for agent in self._agents]:
                # TODO gather and await
                _ = await self._send_message(
                    self._history[-1],
                    agent,
                    cancellation_token=cancellation_token,
                )
                # TODO handle if response is not None

            response = await self._send_message(
                RespondNow(),
                speaker,
                cancellation_token=cancellation_token,
            )

            if response is not None:
                # 4. Append the response to the history.
                self._history.append(response)
                self._output.on_message_received(response)

            # 6. Increment the round.
            round += 1

        output = self._output.get_output()
        self._output.reset()
        self._history.clear()
        return output
