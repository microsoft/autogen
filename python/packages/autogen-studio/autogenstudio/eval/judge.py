# eval/judge.py
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional

from autogen_core import CancellationToken

from ..datamodel.eval import (EvalDimensionScore, EvalJudgeCriteria, EvalScore,
                              EvalTask, EvalRunResult)


class BaseEvalJudge(ABC):
    """Abstract base class for evaluation judges."""
    
    @abstractmethod
    async def judge(
        self,
        task: EvalTask,
        result: EvalRunResult,
        criteria: List[EvalJudgeCriteria],
        cancellation_token: Optional[CancellationToken] = None
    ) -> EvalScore:
        """Judge the result of an evaluation run."""
        pass


class LLMEvalJudge(BaseEvalJudge):
    """Judge that uses an LLM to evaluate results."""
    
    def __init__(self, model_client):
        self.model_client = model_client
    
    async def judge(
        self,
        task: EvalTask,
        result: EvalRunResult,
        criteria: List[EvalJudgeCriteria],
        cancellation_token: Optional[CancellationToken] = None
    ) -> EvalScore:
        """Judge the result using an LLM."""
        # Create a score object
        score = EvalScore(max_value=10.0)
        
        # Judge each dimension in parallel
        dimension_score_tasks = []
        for criterion in criteria:
            dimension_score_tasks.append(
                self._judge_dimension(task, result, criterion, cancellation_token)
            )
        
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
        cancellation_token: Optional[CancellationToken] = None
    ) -> EvalDimensionScore:
        """Judge a specific dimension."""
        # Format task and result for the LLM
        task_description = self._format_task(task)
        result_description = result.model_dump()
        
        # Create the prompt
        prompt = f"""
        You are evaluating the quality of an AI response.
        
        Task: {task_description}
        
        Response: {result_description}
        
        Evaluation criteria: {criterion.dimension}
        {criterion.prompt}
        
        Score the response on a scale from {criterion.min_value} to {criterion.max_value}.
        First, provide a detailed explanation of your evaluation.
        Then, give your final score as a single number between 0 and {criterion.max_value}.
        
        Format your answer as:
        Explanation: [Your detailed evaluation]
        Score: [Number between 0 and {criterion.max_value}]
        """
        
        # Get judgment from LLM
        response = await self.model_client.create([{"role": "user", "content": prompt}])
        
        # Parse the response to extract score and reason
        explanation, score_value = self._parse_judgment(response.content, criterion.max_value)
        
        return EvalDimensionScore(
            dimension=criterion.dimension,
            score=score_value,
            reason=explanation,
            max_value=criterion.max_value
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
        
        # for inp in task.inputs:
        #     if inp.type == "text":
        #         task_parts.append(inp.content)
        
        return "\n".join(task_parts)
    
     
    
    def _parse_judgment(self, judgment_text: str, max_value: float) -> tuple:
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