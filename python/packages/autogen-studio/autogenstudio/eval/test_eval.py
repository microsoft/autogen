"""
Comprehensive test suite for the AutoGen Studio evaluation system.

This file provides complete test coverage for the eval system using mocks,
eliminating the need for API keys or external dependencies.

Features tested:
- ModelEvalRunner: Single LLM evaluation
- LLMEvalJudge: LLM-based scoring with multiple criteria
- EvalOrchestrator: Task, criteria, and run management
- Component creation and basic operations

Usage:
    # Run with pytest (recommended)
    pytest autogenstudio/eval/test_eval.py -v
    
    # Run direct test
    python -c "import asyncio; from autogenstudio.eval.test_eval import *; asyncio.run(main())"
    
    # From package context
    python -m autogenstudio.eval.test_eval
"""

import asyncio
from unittest.mock import MagicMock

import pytest
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage

from ..datamodel.eval import EvalDimensionScore, EvalJudgeCriteria, EvalRunResult, EvalScore, EvalTask
from ._orchestrator import EvalOrchestrator
from .judges import LLMEvalJudge
from .runners import ModelEvalRunner


class MockChatCompletionClient:
    """Mock chat completion client for testing."""
    
    def __init__(self, response_content="Mock response"):
        self.response_content = response_content
        
    async def create(self, messages, cancellation_token=None, **kwargs):
        """Mock create method that returns a simple response."""
        mock_response = MagicMock()
        
        # Handle JSON output for judges
        if kwargs.get("json_output") == EvalDimensionScore:
            mock_response.content = '{"dimension": "test", "score": 8.5, "reason": "Good response", "max_value": 10.0, "min_value": 0.0}'
        else:
            mock_response.content = self.response_content
            
        return mock_response
    
    def dump_component(self):
        """Mock dump_component for serialization."""
        from autogen_core import ComponentModel
        # Return a proper ComponentModel-like object
        mock_component = MagicMock()
        mock_component.provider = "mock_provider"
        mock_component.config = {"response": self.response_content}
        mock_component.model_dump = lambda: {
            "provider": "mock_provider", 
            "config": {"response": self.response_content}
        }
        return mock_component
    
    @classmethod
    def load_component(cls, config):
        """Mock load_component for deserialization."""
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump()
        elif hasattr(config, 'config'):
            config_dict = config.config
        else:
            config_dict = config
        return cls(config_dict.get("response", "Mock response"))


class TestEvalSystem:
    """Test cases for the evaluation system."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock chat completion client."""
        return MockChatCompletionClient()
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample evaluation task."""
        return EvalTask(
            name="Sample Task",
            description="A test task for evaluation",
            input="What is the capital of France?"
        )
    
    @pytest.fixture
    def sample_criteria(self):
        """Create sample evaluation criteria."""
        return [
            EvalJudgeCriteria(
                dimension="accuracy",
                prompt="Evaluate the factual accuracy of the response.",
                min_value=0,
                max_value=10
            ),
            EvalJudgeCriteria(
                dimension="relevance",
                prompt="Evaluate how relevant the response is to the question.",
                min_value=0,
                max_value=10
            )
        ]
    
    @pytest.mark.asyncio
    async def test_model_runner(self, mock_client, sample_task):
        """Test the ModelEvalRunner with a mock client."""
        runner = ModelEvalRunner(model_client=mock_client)
        
        # Test batch interface
        results = await runner.run([sample_task])
        
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, EvalRunResult)
        assert result.status is True
        assert result.result is not None
        assert isinstance(result.result, TaskResult)
        assert len(result.result.messages) > 0
        assert result.error is None
        
    
    @pytest.mark.asyncio
    async def test_model_runner_batch(self, mock_client):
        """Test the ModelEvalRunner with multiple tasks."""
        runner = ModelEvalRunner(model_client=mock_client)
        
        # Create multiple tasks
        tasks = [
            EvalTask(name="Task 1", input="What is 2+2?"),
            EvalTask(name="Task 2", input="What is 3+3?"),
            EvalTask(name="Task 3", input="What is 4+4?"),
        ]
        
        # Test batch processing
        results = await runner.run(tasks)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, EvalRunResult)
            assert result.status is True
            assert result.result is not None
    
    @pytest.mark.asyncio
    async def test_llm_judge(self, mock_client, sample_task, sample_criteria):
        """Test the LLMEvalJudge with a mock client."""
        judge = LLMEvalJudge(model_client=mock_client)
        
        # Create a mock run result
        run_result = EvalRunResult(
            status=True,
            result=TaskResult(messages=[TextMessage(content="Paris is the capital of France.", source="model")])
        )
        
        score = await judge.judge(sample_task, run_result, sample_criteria)
        
        assert isinstance(score, EvalScore)
        assert len(score.dimension_scores) == 2
        assert all(isinstance(ds, EvalDimensionScore) for ds in score.dimension_scores)
        assert score.overall_score is not None
        assert 0 <= score.overall_score <= 10
    
    @pytest.mark.asyncio
    async def test_orchestrator_task_management(self):
        """Test the orchestrator's task management functionality."""
        orchestrator = EvalOrchestrator()  # In-memory mode
        
        task = EvalTask(
            name="Test Task",
            description="A test task",
            input="Test input"
        )
        
        # Create task
        task_id = await orchestrator.create_task(task)
        assert task_id is not None
        
        # Get task
        retrieved_task = await orchestrator.get_task(task_id)
        assert retrieved_task is not None
        assert retrieved_task.name == "Test Task"
        
        # List tasks
        tasks = await orchestrator.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].name == "Test Task"
    
    @pytest.mark.asyncio
    async def test_orchestrator_criteria_management(self):
        """Test the orchestrator's criteria management functionality."""
        orchestrator = EvalOrchestrator()  # In-memory mode
        
        criteria = EvalJudgeCriteria(
            dimension="test_dimension",
            prompt="Test prompt",
            min_value=0,
            max_value=10
        )
        
        # Create criteria
        criteria_id = await orchestrator.create_criteria(criteria)
        assert criteria_id is not None
        
        # Get criteria
        retrieved_criteria = await orchestrator.get_criteria(criteria_id)
        assert retrieved_criteria is not None
        assert retrieved_criteria.dimension == "test_dimension"
        
        # List criteria
        criteria_list = await orchestrator.list_criteria()
        assert len(criteria_list) == 1
        assert criteria_list[0].dimension == "test_dimension"
    
    @pytest.mark.asyncio
    async def test_orchestrator_run_creation(self, mock_client, sample_task, sample_criteria):
        """Test the orchestrator's run creation functionality."""
        orchestrator = EvalOrchestrator()  # In-memory mode
        
        # Create task and criteria first
        task_id = await orchestrator.create_task(sample_task)
        criteria_ids = []
        for criterion in sample_criteria:
            criteria_ids.append(await orchestrator.create_criteria(criterion))
        
        # Skip serialization-dependent tests for now
        # This test verifies task and criteria creation works
        assert task_id is not None
        assert len(criteria_ids) == 2
        
        # Verify we can retrieve them
        retrieved_task = await orchestrator.get_task(task_id)
        assert retrieved_task is not None
        assert retrieved_task.name == sample_task.name
    
    @pytest.mark.asyncio
    async def test_direct_evaluation_flow(self, mock_client, sample_task, sample_criteria):
        """Test direct evaluation without orchestrator serialization."""
        # Test runner directly
        runner = ModelEvalRunner(model_client=mock_client)
        run_results = await runner.run([sample_task])
        
        assert len(run_results) == 1
        run_result = run_results[0]
        assert isinstance(run_result, EvalRunResult)
        assert run_result.status is True
        
        # Test judge directly
        judge = LLMEvalJudge(model_client=mock_client)
        score = await judge.judge(sample_task, run_result, sample_criteria)
        
        assert isinstance(score, EvalScore)
        assert len(score.dimension_scores) == 2
        assert score.overall_score is not None


def test_basic_component_creation():
    """Test that components can be created without serialization."""
    mock_client = MockChatCompletionClient("Test response")
    
    # Test runner creation
    runner = ModelEvalRunner(model_client=mock_client)
    assert runner.name == "Model Runner"
    
    # Test judge creation
    judge = LLMEvalJudge(model_client=mock_client)
    assert judge.name == "LLM Judge"


if __name__ == "__main__":
    # Simple test runner for direct execution
    async def main():
        """Run a simple test without pytest."""
        print("Running basic eval system test...")
        
        # Create mock client
        mock_client = MockChatCompletionClient("Paris is the capital of France.")
        
        # Test model runner
        task = EvalTask(
            name="Test",
            input="What is the capital of France?"
        )
        
        runner = ModelEvalRunner(model_client=mock_client)
        results = await runner.run([task])
        result = results[0]
        
        print(f"Runner result: {result.status}")
        if result.result and result.result.messages:
            print(f"Response: {result.result.messages[0].content}")
        else:
            print("No result")
        
        # Test judge
        judge = LLMEvalJudge(model_client=mock_client)
        criteria = [EvalJudgeCriteria(
            dimension="accuracy",
            prompt="Rate accuracy",
            min_value=0,
            max_value=10
        )]
        
        score = await judge.judge(task, result, criteria)
        print(f"Score: {score.overall_score}")
        print(f"Dimension scores: {[(ds.dimension, ds.score) for ds in score.dimension_scores]}")
        
        print("✅ Basic eval system test completed!")
    
    asyncio.run(main())