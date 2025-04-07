import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from autogen_core import CancellationToken, Component, ComponentBase
from autogen_core.models import ChatCompletionClient, UserMessage
from loguru import logger
from pydantic import BaseModel
from typing_extensions import Self

from ..datamodel.eval import EvalDimensionScore, EvalJudgeCriteria, EvalRunResult, EvalScore, EvalTask


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


class LLMEvalJudgeConfig(BaseEvalJudgeConfig):
    """Configuration for LLMEvalJudge."""

    model_client: Any  # ComponentModel


class LLMEvalJudge(BaseEvalJudge, Component[LLMEvalJudgeConfig]):
    """Judge that uses an LLM to evaluate results."""

    component_config_schema = LLMEvalJudgeConfig
    component_type = "eval_judge"
    component_provider_override = "autogenstudio.eval.judges.LLMEvalJudge"

    def __init__(
        self,
        model_client: ChatCompletionClient,
        name: str = "LLM Judge",
        description: str = "Evaluates results using an LLM",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, description, metadata)
        self.model_client = model_client

    async def judge(
        self,
        task: EvalTask,
        result: EvalRunResult,
        criteria: List[EvalJudgeCriteria],
        cancellation_token: Optional[CancellationToken] = None,
    ) -> EvalScore:
        """Judge the result using an LLM."""
        # Create a score object
        score = EvalScore(max_value=10.0)

        # Judge each dimension in parallel
        dimension_score_tasks = []
        for criterion in criteria:
            dimension_score_tasks.append(self._judge_dimension(task, result, criterion, cancellation_token))

        dimension_scores = await asyncio.gather(*dimension_score_tasks)
        score.dimension_scores = dimension_scores

        # Calculate overall score (average of dimension scores)
        valid_scores = [ds.score for ds in dimension_scores if ds.score is not None]
        if valid_scores:
            score.overall_score = sum(valid_scores) / len(valid_scores)

        return score

    async def _judge_dimension(
        self,
        task: EvalTask,
        result: EvalRunResult,
        criterion: EvalJudgeCriteria,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> EvalDimensionScore:
        """Judge a specific dimension."""
        # Format task and result for the LLM
        task_description = self._format_task(task)
        result_description = result.model_dump()

        # Create the prompt
        prompt = f"""
        You are evaluating the quality of a system response to a task.
        Task: {task_description}Response: {result_description}
        Evaluation criteria: {criterion.dimension}
        {criterion.prompt}
        Score the response on a scale from {criterion.min_value} to {criterion.max_value}.
        First, provide a detailed explanation of your evaluation.
        Then, give your final score as a single number between 0 and {criterion.max_value}.
        Format your answer should be a json for the EvalDimensionScore class:
        {{
            "dimension": "{criterion.dimension}",
            "reason": "<explanation>",
            "score": <score>
        }}
        Please ensure the score is a number between {criterion.min_value} and {criterion.max_value}.
        If you cannot evaluate the response, please return a score of null.
        If the response is not relevant, please return a score of 0.
        If the response is perfect, please return a score of {criterion.max_value}.
        If the response is not relevant, please return a score of 0.
        If the response is perfect, please return a score of {criterion.max_value}.
        """

        # Get judgment from LLM
        model_input = []
        text_message = UserMessage(content=prompt, source="user")
        model_input.append(text_message)

        # Run with the model client in the same format as used in runners
        model_result = await self.model_client.create(
            messages=model_input,
            cancellation_token=cancellation_token,
            json_output=EvalDimensionScore,
        )

        # Extract content from the response
        model_response = model_result.content if isinstance(model_result.content, str) else str(model_result.content)

        try:
            # validate response string as EvalDimensionScore
            model_response = EvalDimensionScore.model_validate_json(model_response)
            return model_response
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}", model_result.content)
            return EvalDimensionScore(
                dimension=criterion.dimension,
                reason="Failed to parse response",
                score=0.0,
                max_value=criterion.max_value,
                min_value=criterion.min_value,
            )

    def _format_task(self, task: EvalTask) -> str:
        """Format the task for the LLM."""
        task_parts = []

        if task.description:
            task_parts.append(task.description)
        if isinstance(task.input, str):
            task_parts.append(task.input)
        elif isinstance(task.input, list):
            task_parts.append("\n".join(str(x) for x in task.input if isinstance(x, str)))

        return "\n".join(task_parts)

    def _parse_judgment(self, judgment_text: str, max_value: float) -> Tuple[str, Optional[float]]:
        """Parse judgment text to extract explanation and score."""
        explanation = ""
        score = None

        # Simple parsing - could be improved with regex
        lines = judgment_text.split("\n")
        for line in lines:
            if line.strip().lower().startswith("explanation:"):
                explanation = line.split(":", 1)[1].strip()
            elif line.strip().lower().startswith("score:"):
                try:
                    score_str = line.split(":", 1)[1].strip()
                    score = float(score_str)
                    # Ensure score is within bounds
                    score = min(max(score, 0), max_value)
                except (ValueError, IndexError):
                    pass

        return explanation, score

    def _to_config(self) -> LLMEvalJudgeConfig:
        """Convert to configuration object including model client configuration."""
        base_config = super()._to_config()
        return LLMEvalJudgeConfig(
            name=base_config.name,
            description=base_config.description,
            metadata=base_config.metadata,
            model_client=self.model_client.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: LLMEvalJudgeConfig) -> Self:
        """Create from configuration object with serialized model client."""
        model_client = ChatCompletionClient.load_component(config.model_client)
        return cls(
            model_client=model_client, name=config.name, description=config.description, metadata=config.metadata
        )


# # Usage example
# async def example_usage():
#     # Create a model client
#     from autogen_ext.models import OpenAIChatCompletionClient

#     model_client = OpenAIChatCompletionClient(
#         model="gpt-4",
#         api_key="your-api-key"
#     )

#     # Create a judge
#     llm_judge = LLMEvalJudge(model_client=model_client)

#     # Serialize the judge to a ComponentModel
#     judge_config = llm_judge.dump_component()
#     print(f"Serialized judge: {judge_config}")

#     # Deserialize back to a LLMEvalJudge
#     deserialized_judge = LLMEvalJudge.load_component(judge_config)

#     # Create criteria for evaluation
#     criteria = [
#         EvalJudgeCriteria(
#             dimension="relevance",
#             prompt="Evaluate how relevant the response is to the query.",
#             min_value=0,
#             max_value=10
#         ),
#         EvalJudgeCriteria(
#             dimension="accuracy",
#             prompt="Evaluate the factual accuracy of the response.",
#             min_value=0,
#             max_value=10
#         )
#     ]

#     # Create a mock task and result
#     task = EvalTask(
#         id="task-123",
#         name="Sample Task",
#         description="A sample task for evaluation",
#         input="What is the capital of France?"
#     )

#     result = EvalRunResult(
#         status=True,
#         result={
#             "messages": [{"content": "The capital of France is Paris.", "source": "model"}]
#         }
#     )

#     # Run the evaluation
#     score = await deserialized_judge.judge(task, result, criteria)
#     print(f"Evaluation score: {score}")
