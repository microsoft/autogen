from typing import Any, Mapping, Sequence

import torch
import torch.nn.functional as F

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_core import CancellationToken, Component
from pydantic import BaseModel
from torchagentic.nn.planner import ValueIteration, MCTSPlanner


class TorchAgenticPlannerConfig(BaseModel):
    name: str
    description: str
    num_states: int = 64
    num_actions: int = 8
    planner_type: str = "vi"
    gamma: float = 0.99


class TorchAgenticPlannerAgent(BaseChatAgent, Component[TorchAgenticPlannerConfig]):
    component_config_schema = TorchAgenticPlannerConfig
    component_provider_override = (
        "autogen_ext.agents.torchagentic.TorchAgenticPlannerAgent"
    )

    def __init__(
        self,
        name: str,
        description: str = "A differentiable planning agent using value iteration or MCTS.",
        num_states: int = 64,
        num_actions: int = 8,
        planner_type: str = "vi",
        gamma: float = 0.99,
    ) -> None:
        super().__init__(name, description)
        self._num_states = num_states
        self._num_actions = num_actions
        self._gamma = gamma

        if planner_type == "vi":
            self._planner = ValueIteration(
                num_states=num_states,
                num_actions=num_actions,
                gamma=gamma,
                num_iters=20,
            )
        elif planner_type == "mcts":
            self._planner = MCTSPlanner(
                num_simulations=20,
                c_puct=1.25,
                gamma=gamma,
            )
        else:
            raise ValueError(f"Unknown planner_type: {planner_type}")
        self._planner_type = planner_type
        self._chat_history: list[BaseChatMessage] = []

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        self._chat_history.extend(messages)

        with torch.no_grad():
            S, A = self._num_states, self._num_actions
            reward = torch.randn(1, S, A)
            kernel = torch.randn(1, S, A, S)
            kernel = F.softmax(kernel.reshape(1, S * A, S), dim=-1).reshape(1, S, A, S)

            if self._planner_type == "vi":
                values, q_values = self._planner(reward, kernel)
                best_q = q_values.max(dim=-1).values.squeeze(0)
                top_states = best_q.topk(min(3, S)).indices.tolist()
                plan_summary = f"top states: {top_states}"
            else:
                prior = torch.randn(1, A)
                value = torch.randn(1)
                probs, _ = self._planner(prior, value)
                top_actions = probs.topk(min(3, A), dim=-1).indices.squeeze(0).tolist()
                plan_summary = f"top actions: {top_actions}"

        content = (
            f"[TorchAgentic | {self._planner_type.upper()} | "
            f"{plan_summary} | states: {S} | actions: {A}]"
        )
        return Response(
            chat_message=TextMessage(content=content, source=self.name),
            inner_messages=list(messages),
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self._chat_history.clear()

    def _to_config(self) -> TorchAgenticPlannerConfig:
        return TorchAgenticPlannerConfig(
            name=self.name,
            description=self.description,
            num_states=self._num_states,
            num_actions=self._num_actions,
            planner_type=self._planner_type,
            gamma=self._gamma,
        )

    @classmethod
    def _from_config(cls, config: TorchAgenticPlannerConfig) -> "TorchAgenticPlannerAgent":
        return cls(
            name=config.name,
            description=config.description,
            num_states=config.num_states,
            num_actions=config.num_actions,
            planner_type=config.planner_type,
            gamma=config.gamma,
        )
