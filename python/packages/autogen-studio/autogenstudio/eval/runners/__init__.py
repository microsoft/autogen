from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from autogen_core import CancellationToken, ComponentBase
from pydantic import BaseModel

from ...datamodel.eval import EvalRunResult, EvalTask


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
    async def run(self, tasks: list[EvalTask], cancellation_token: Optional[CancellationToken] = None) -> list[EvalRunResult]:
        """Run the evaluation on the provided tasks and return results.

        Args:
            tasks: The list of tasks to evaluate
            cancellation_token: Optional token to cancel the evaluation

        Returns:
            List[EvalRunResult]: The results of the evaluations, one per task
        """
        pass


    def _to_config(self) -> BaseEvalRunnerConfig:
        """Convert the runner configuration to a configuration object for serialization."""
        return BaseEvalRunnerConfig(name=self.name, description=self.description, metadata=self.metadata)


# Import specific runner implementations
from ._model import ModelEvalRunner, ModelEvalRunnerConfig
from ._team import TeamEvalRunner, TeamEvalRunnerConfig

__all__ = ["BaseEvalRunner", "BaseEvalRunnerConfig", "ModelEvalRunner", "ModelEvalRunnerConfig", "TeamEvalRunner", "TeamEvalRunnerConfig"]