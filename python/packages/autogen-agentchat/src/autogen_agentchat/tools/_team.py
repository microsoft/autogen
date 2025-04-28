from autogen_core import Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from autogen_agentchat.teams import BaseGroupChat

from ._task_runner_tool import TaskRunnerTool


class TeamToolConfig(BaseModel):
    """Configuration for the TeamTool."""

    name: str
    description: str
    team: ComponentModel


class TeamTool(TaskRunnerTool, Component[TeamToolConfig]):
    """Tool that can be used to run a task.

    The tool returns the result of the task execution as a :class:`~autogen_agentchat.base.TaskResult` object.

    Args:
        team (BaseGroupChat): The team to be used for running the task.
        name (str): The name of the tool.
        description (str): The description of the tool.
    """

    component_config_schema = TeamToolConfig
    component_provider_override = "autogen_agentchat.tools.TeamTool"

    def __init__(self, team: BaseGroupChat, name: str, description: str) -> None:
        self._team = team
        super().__init__(team, name, description)

    def _to_config(self) -> TeamToolConfig:
        return TeamToolConfig(
            name=self._name,
            description=self._description,
            team=self._team.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: TeamToolConfig) -> Self:
        return cls(BaseGroupChat.load_component(config.team), config.name, config.description)
