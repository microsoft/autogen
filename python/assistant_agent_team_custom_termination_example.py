import asyncio
from typing import Sequence
from autogen_agentchat.base import TerminatedException, TerminationCondition
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, StopMessage, ToolCallExecutionEvent
from autogen_core import Component
from pydantic import BaseModel
from typing_extensions import Self
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Custom termination config and condition
class FunctionCallTerminationConfig(BaseModel):
    function_name: str

class FunctionCallTermination(TerminationCondition, Component[FunctionCallTerminationConfig]):
    component_config_schema = FunctionCallTerminationConfig
    component_provider_override = "autogen_agentchat.conditions.FunctionCallTermination"
    def __init__(self, function_name: str) -> None:
        self._terminated = False
        self._function_name = function_name
    @property
    def terminated(self) -> bool:
        return self._terminated
    async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        for message in messages:
            if isinstance(message, ToolCallExecutionEvent):
                for execution in message.content:
                    if execution.name == self._function_name:
                        self._terminated = True
                        return StopMessage(
                            content=f"Function '{self._function_name}' was executed.",
                            source="FunctionCallTermination",
                        )
        return None
    async def reset(self) -> None:
        self._terminated = False
    def _to_config(self) -> FunctionCallTerminationConfig:
        return FunctionCallTerminationConfig(function_name=self._function_name)
    @classmethod
    def _from_config(cls, config: FunctionCallTerminationConfig) -> Self:
        return cls(function_name=config.function_name)

def approve() -> None:
    """Approve the message when all feedbacks have been addressed."""
    pass

async def main():
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        temperature=1,
    )
    primary_agent = AssistantAgent(
        "primary",
        model_client=model_client,
        system_message="You are a helpful AI assistant.",
    )
    critic_agent = AssistantAgent(
        "critic",
        model_client=model_client,
        tools=[approve],
        system_message="Provide constructive feedback. Use the approve tool to approve when all feedbacks are addressed.",
    )
    function_call_termination = FunctionCallTermination(function_name="approve")
    round_robin_team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=function_call_termination)
    await Console(round_robin_team.run_stream(task="Write a unique, Haiku about the weather in Paris"))
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
