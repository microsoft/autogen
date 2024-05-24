from typing import Any, List, Protocol, Sequence

from agnext.chat.types import Reset, RespondNow

from ...core.agent_runtime import AgentRuntime
from ...core.cancellation_token import CancellationToken
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

    async def on_message(
        self, message: Any, require_response: bool, cancellation_token: CancellationToken
    ) -> Any | None:
        if isinstance(message, Reset):
            # Reset the history.
            self._history = []
            # TODO: reset sub-agents?

        if isinstance(message, RespondNow):
            # TODO reset...
            return self._output.get_output()

        # TODO: should we do nothing here?
        # Perhaps it should be saved into the message history?
        if not require_response:
            return None

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
                    require_response=False,
                    cancellation_token=cancellation_token,
                )

            response = await self._send_message(
                RespondNow(),
                speaker,
                require_response=True,
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
        return output
