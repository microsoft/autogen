import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken, Component, ComponentModel
from autogen_core.models import ChatCompletionClient, UserMessage
from typing_extensions import Self

from ...datamodel.eval import EvalRunResult, EvalTask
from . import BaseEvalRunner, BaseEvalRunnerConfig


class ModelEvalRunnerConfig(BaseEvalRunnerConfig):
    """Configuration for ModelEvalRunner."""

    model_client: ComponentModel


class ModelEvalRunner(BaseEvalRunner, Component[ModelEvalRunnerConfig]):
    """Evaluation runner that uses a single LLM to process tasks.

    This runner sends the task directly to a model client and returns the response.
    """

    component_config_schema = ModelEvalRunnerConfig
    component_type = "eval_runner"
    component_provider_override = "autogenstudio.eval.runners._model.ModelEvalRunner"

    def __init__(
        self,
        model_client: ChatCompletionClient,
        name: str = "Model Runner",
        description: str = "Evaluates tasks using a single LLM",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, description, metadata)
        self.model_client = model_client

    async def run(self, tasks: list[EvalTask], cancellation_token: Optional[CancellationToken] = None) -> list[EvalRunResult]:
        """Run the tasks with the model client and return the results."""
        if not tasks:
            return []
        
        # Process tasks in parallel with concurrency control
        max_concurrent = min(10, len(tasks))  # Limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_single_task(task: EvalTask) -> EvalRunResult:
            """Run a single task with concurrency control."""
            async with semaphore:
                return await self._run_single_task(task, cancellation_token)
        
        # Execute all tasks in parallel
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
    
    async def _run_single_task(self, task: EvalTask, cancellation_token: Optional[CancellationToken] = None) -> EvalRunResult:
        """Run a single task with the model client."""
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
            return EvalRunResult(result=task_result, status=True, start_time=datetime.now(), end_time=datetime.now())

        except Exception as e:
            return EvalRunResult(status=False, error=str(e), end_time=datetime.now())

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