from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from autogen_core import CancellationToken, ComponentBase
from pydantic import BaseModel

from ...datamodel.eval import EvalJudgeCriteria, EvalRunResult, EvalScore, EvalTask


class BaseEvalJudgeConfig(BaseModel):
    """Base configuration for evaluation judges."""

    name: str = "Base Judge"
    description: str = ""
    metadata: Dict[str, Any] = {}


class BaseEvalJudge(ABC, ComponentBase[BaseEvalJudgeConfig]):
    """Abstract base class for evaluation judges."""

    component_type = "eval_judge"

    def __init__(self, name: str = "Base Judge", description: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.metadata = metadata or {}

    @abstractmethod
    async def judge(
        self,
        task: EvalTask,
        result: EvalRunResult,
        criteria: List[EvalJudgeCriteria],
        cancellation_token: Optional[CancellationToken] = None,
    ) -> EvalScore:
        """Judge the result of an evaluation run."""
        pass

    def _to_config(self) -> BaseEvalJudgeConfig:
        """Convert the judge configuration to a configuration object for serialization."""
        return BaseEvalJudgeConfig(name=self.name, description=self.description, metadata=self.metadata)


# Import specific judge implementations
from ._llm import LLMEvalJudge, LLMEvalJudgeConfig

__all__ = ["BaseEvalJudge", "BaseEvalJudgeConfig", "LLMEvalJudge", "LLMEvalJudgeConfig"]