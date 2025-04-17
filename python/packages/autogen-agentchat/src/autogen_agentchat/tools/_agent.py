from autogen_core import Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from autogen_agentchat.agents import BaseChatAgent

from ._task_runner_tool import TaskRunnerTool


class AgentToolConfig(BaseModel):
    """Configuration for the AgentTool."""

    agent: ComponentModel


class AgentTool(TaskRunnerTool, Component[AgentToolConfig]):
    """Tool that can be used to run a task using an agent.

    The tool returns the result of the task execution as a :class:`~autogen_agentchat.base.TaskResult` object.

    Args:
        agent (BaseChatAgent): The agent to be used for running the task.
    """

    component_config_schema = AgentToolConfig
    component_provider_override = "autogen_agentchat.tools.AgentTool"

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
