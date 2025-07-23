import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Union

from autogen_agentchat.base import Team
from autogen_agentchat.messages import ChatMessage, MultiModalMessage, TextMessage
from autogen_core import CancellationToken, Component, ComponentModel, Image
from typing_extensions import Self

from ...datamodel.eval import EvalRunResult, EvalTask
from . import BaseEvalRunner, BaseEvalRunnerConfig


class TeamEvalRunnerConfig(BaseEvalRunnerConfig):
    """Configuration for TeamEvalRunner."""

    team: ComponentModel


class TeamEvalRunner(BaseEvalRunner, Component[TeamEvalRunnerConfig]):
    """Evaluation runner that uses a team of agents to process tasks.

    This runner creates and runs a team based on a team configuration.
    """

    component_config_schema = TeamEvalRunnerConfig
    component_type = "eval_runner"
    component_provider_override = "autogenstudio.eval.runners._team.TeamEvalRunner"

    def __init__(
        self,
        team: Union[Team, ComponentModel],
        name: str = "Team Runner",
        description: str = "Evaluates tasks using a team of agents",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, description, metadata)
        self._team = team if isinstance(team, Team) else Team.load_component(team)

    async def run(self, tasks: list[EvalTask], cancellation_token: Optional[CancellationToken] = None) -> list[EvalRunResult]:
        """Run the tasks with isolated team instances and return the results."""
        if not tasks:
            return []
        
        # Each task gets a fresh team instance to maintain isolation
        async def run_single_task(task: EvalTask) -> EvalRunResult:
            """Run a single task with a fresh team instance."""
            try:
                # Create a fresh team instance from the stored configuration
                fresh_team = Team.load_component(self._team.dump_component())
                
                # Convert task input to team format
                team_task: Sequence[ChatMessage] = []
                if isinstance(task.input, str):
                    team_task.append(TextMessage(content=task.input, source="user"))
                elif isinstance(task.input, list):
                    for message in task.input:
                        if isinstance(message, str):
                            team_task.append(TextMessage(content=message, source="user"))
                        elif isinstance(message, Image):
                            team_task.append(MultiModalMessage(source="user", content=[message]))

                # Run task with fresh team
                team_result = await fresh_team.run(task=team_task, cancellation_token=cancellation_token)

                return EvalRunResult(result=team_result, status=True, start_time=datetime.now(), end_time=datetime.now())

            except Exception as e:
                return EvalRunResult(status=False, error=str(e), end_time=datetime.now())
        
        # Run all tasks in parallel with isolated team instances
        results = await asyncio.gather(
            *[run_single_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # Convert exceptions to failed EvalRunResults
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(EvalRunResult(
                    status=False, 
                    error=str(result), 
                    end_time=datetime.now()
                ))
            else:
                processed_results.append(result)
        
        return processed_results

    def _to_config(self) -> TeamEvalRunnerConfig:
        """Convert to configuration object including team configuration."""
        base_config = super()._to_config()
        return TeamEvalRunnerConfig(
            name=base_config.name,
            description=base_config.description,
            metadata=base_config.metadata,
            team=self._team.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: TeamEvalRunnerConfig) -> Self:
        """Create from configuration object with serialized team configuration."""
        return cls(
            team=Team.load_component(config.team),
            name=config.name,
            description=config.description,
            metadata=config.metadata,
        )