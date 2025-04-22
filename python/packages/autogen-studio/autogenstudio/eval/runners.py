from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Type, Union

from autogen_agentchat.base import TaskResult, Team
from autogen_agentchat.messages import ChatMessage, MultiModalMessage, TextMessage
from autogen_core import CancellationToken, Component, ComponentBase, ComponentModel, Image
from autogen_core.models import ChatCompletionClient, UserMessage
from pydantic import BaseModel
from typing_extensions import Self

from ..datamodel.eval import EvalRunResult, EvalTask


class BaseEvalRunnerConfig(BaseModel):
    """Base configuration for evaluation runners."""

    name: str
    description: str = ""
    metadata: Dict[str, Any] = {}


class BaseEvalRunner(ABC, ComponentBase[BaseEvalRunnerConfig]):
    """Base class for evaluation runners that defines the interface for running evaluations.

    This class provides the core interface that all evaluation runners must implement.
    Subclasses should implement the run method to define how a specific evaluation is executed.
    """

    component_type = "eval_runner"

    def __init__(self, name: str, description: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.metadata = metadata or {}

    @abstractmethod
    async def run(self, task: EvalTask, cancellation_token: Optional[CancellationToken] = None) -> EvalRunResult:
        """Run the evaluation on the provided task and return a result.

        Args:
            task: The task to evaluate
            cancellation_token: Optional token to cancel the evaluation

        Returns:
            EvaluationResult: The result of the evaluation
        """
        pass

    def _to_config(self) -> BaseEvalRunnerConfig:
        """Convert the runner configuration to a configuration object for serialization."""
        return BaseEvalRunnerConfig(name=self.name, description=self.description, metadata=self.metadata)


class ModelEvalRunnerConfig(BaseEvalRunnerConfig):
    """Configuration for ModelEvalRunner."""

    model_client: ComponentModel


class ModelEvalRunner(BaseEvalRunner, Component[ModelEvalRunnerConfig]):
    """Evaluation runner that uses a single LLM to process tasks.

    This runner sends the task directly to a model client and returns the response.
    """

    component_config_schema = ModelEvalRunnerConfig
    component_type = "eval_runner"
    component_provider_override = "autogenstudio.eval.runners.ModelEvalRunner"

    def __init__(
        self,
        model_client: ChatCompletionClient,
        name: str = "Model Runner",
        description: str = "Evaluates tasks using a single LLM",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, description, metadata)
        self.model_client = model_client

    async def run(self, task: EvalTask, cancellation_token: Optional[CancellationToken] = None) -> EvalRunResult:
        """Run the task with the model client and return the result."""
        # Create initial result object
        result = EvalRunResult()

        try:
            model_input = []
            if isinstance(task.input, str):
                text_message = UserMessage(content=task.input, source="user")
                model_input.append(text_message)
            elif isinstance(task.input, list):
                message_content = [x for x in task.input]
                model_input.append(UserMessage(content=message_content, source="user"))
            # Run with the model
            model_result = await self.model_client.create(messages=model_input, cancellation_token=cancellation_token)

            model_response = model_result.content if isinstance(model_result, str) else model_result.model_dump()

            task_result = TaskResult(
                messages=[TextMessage(content=str(model_response), source="model")],
            )
            result = EvalRunResult(result=task_result, status=True, start_time=datetime.now(), end_time=datetime.now())

        except Exception as e:
            result = EvalRunResult(status=False, error=str(e), end_time=datetime.now())

        return result

    def _to_config(self) -> ModelEvalRunnerConfig:
        """Convert to configuration object including model client configuration."""
        base_config = super()._to_config()
        return ModelEvalRunnerConfig(
            name=base_config.name,
            description=base_config.description,
            metadata=base_config.metadata,
            model_client=self.model_client.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: ModelEvalRunnerConfig) -> Self:
        """Create from configuration object with serialized model client."""
        model_client = ChatCompletionClient.load_component(config.model_client)
        return cls(
            name=config.name,
            description=config.description,
            metadata=config.metadata,
            model_client=model_client,
        )


class TeamEvalRunnerConfig(BaseEvalRunnerConfig):
    """Configuration for TeamEvalRunner."""

    team: ComponentModel


class TeamEvalRunner(BaseEvalRunner, Component[TeamEvalRunnerConfig]):
    """Evaluation runner that uses a team of agents to process tasks.

    This runner creates and runs a team based on a team configuration.
    """

    component_config_schema = TeamEvalRunnerConfig
    component_type = "eval_runner"
    component_provider_override = "autogenstudio.eval.runners.TeamEvalRunner"

    def __init__(
        self,
        team: Union[Team, ComponentModel],
        name: str = "Team Runner",
        description: str = "Evaluates tasks using a team of agents",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, description, metadata)
        self._team = team if isinstance(team, Team) else Team.load_component(team)

    async def run(self, task: EvalTask, cancellation_token: Optional[CancellationToken] = None) -> EvalRunResult:
        """Run the task with the team and return the result."""
        # Create initial result object
        result = EvalRunResult()

        try:
            team_task: Sequence[ChatMessage] = []
            if isinstance(task.input, str):
                team_task.append(TextMessage(content=task.input, source="user"))
            if isinstance(task.input, list):
                for message in task.input:
                    if isinstance(message, str):
                        team_task.append(TextMessage(content=message, source="user"))
                    elif isinstance(message, Image):
                        team_task.append(MultiModalMessage(source="user", content=[message]))

            # Run task with team
            team_result = await self._team.run(task=team_task, cancellation_token=cancellation_token)

            result = EvalRunResult(result=team_result, status=True, start_time=datetime.now(), end_time=datetime.now())

        except Exception as e:
            result = EvalRunResult(status=False, error=str(e), end_time=datetime.now())

        return result

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
