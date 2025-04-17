from typing import Any, Mapping

from autogen_core import Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.state import BaseState

from ._task_runner_tool import TaskRunnerTool


class AgentToolConfig(BaseModel):
    """Configuration for the AgentTool."""

    agent: ComponentModel


class AgentTool(TaskRunnerTool, Component[AgentToolConfig]):
    """Tool that can be used to run a task."""

    component_config_schema = AgentToolConfig
    component_provider_override = "autogen_ext.tools.nested.AgentTool"

    def __init__(self, agent: BaseChatAgent) -> None:
        self._agent = agent
        super().__init__(agent, agent.name, agent.description)

    def _to_config(self) -> AgentToolConfig:
        return AgentToolConfig(
            agent=self._agent.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: AgentToolConfig) -> Self:
        return cls(BaseChatAgent.load_component(config.agent))
