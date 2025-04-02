# eval/config.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Union
 
from autogen_core import CancellationToken, ComponentModel, Image
from autogen_core.models import UserMessage
from autogen_agentchat.messages import   TextChatMessage, MultiModalMessage, ChatMessage
from autogen_core.models import ChatCompletionClient , UserMessage 
from autogen_agentchat.base import TaskResult, Team 
from ..datamodel.eval import EvalTask, EvalRunResult


class BaseEvalRunner(ABC):
    """Base class for evaluation runners that defines the interface for running evaluations.
    
    This class provides the core interface that all evaluation runners must implement.
    Subclasses should implement the run method to define how a specific evaluation is executed.
    """
    
    def __init__(self, name: str, description: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.metadata = metadata or {}
        self.id = None  # Assigned when stored in DB
    
    @abstractmethod
    async def run(
        self,
        task: EvalTask,
        cancellation_token: Optional[CancellationToken] = None
    ) -> EvalRunResult:
        """Run the evaluation on the provided task and return a result.
        
        Args:
            task: The task to evaluate
            cancellation_token: Optional token to cancel the evaluation
            
        Returns:
            EvaluationResult: The result of the evaluation
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the runner configuration to a dictionary for storage."""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEvalRunner":
        """Create a runner from a dictionary representation."""
        # This should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement from_dict")


class ModelEvalRunner(BaseEvalRunner):
    """Evaluation runner that uses a single LLM to process tasks.
    
    This runner sends the task directly to a model client and returns the response.
    """
    
    def __init__(
        self, 
        model_client: ChatCompletionClient,
        name: str = "Model Runner",
        description: str = "Evaluates tasks using a single LLM",
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(name, description, metadata)
        self.model_client = model_client
    
    async def run(
        self,
        task: EvalTask,
        cancellation_token: Optional[CancellationToken] = None
    ) -> EvalRunResult:
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
                model_input.append(
                    UserMessage(content=message_content, source="user")
                ) 
            # Run with the model
            model_result = await self.model_client.create(messages= model_input,
                cancellation_token=cancellation_token
            )

            model_response = model_result.content if isinstance(model_result, str) else model_result.model_dump()

            task_result = TaskResult(
                messages=[TextChatMessage(content=str(model_response), source="model")],
            )
            result = EvalRunResult(
                result=task_result,
                status=True,
                start_time=datetime.now(),
                end_time=datetime.now() )
            
        except Exception as e:
            result = EvalRunResult(
                status=False,
                error=str(e),
                end_time=datetime.now()
            )
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation including model configuration."""
        data = super().to_dict()
        # Add model client info (this would need customization based on your model client structure)
        data["model_config"] = {
            "model": getattr(self.model_client, "model", "unknown"),
            # Add other relevant model client parameters
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], model_client):
        """Create from dictionary representation with provided model client."""
        return cls(
            model_client=model_client,
            name=data.get("name", "Model Runner"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )


class TeamEvalRunner(BaseEvalRunner):
    """Evaluation runner that uses a team of agents to process tasks.
    
    This runner creates and runs a team based on a team configuration.
    """
    
    def __init__(
        self, 
        team_manager,
        team_config: Union[Dict[str, Any], ComponentModel],
        name: str = "Team Runner",
        description: str = "Evaluates tasks using a team of agents",
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(name, description, metadata)
        self.team_manager = team_manager
        self.team_config = team_config
    
    async def run(
        self,
        task: EvalTask,
        cancellation_token: Optional[CancellationToken] = None
    ) -> EvalRunResult:
        """Run the task with the team and return the result."""
        # Create initial result object
        result = EvalRunResult()
        
        try:
             
            # Create team from config 
            team = Team.load_component(self.team_config)

            team_task: Sequence[ChatMessage] = [] 
            if isinstance(task.input, str):
                team_task.append(TextChatMessage(content=task.input, source="user"))
            if isinstance(task.input, list): 
                for message in task.input:
                    if isinstance(message, str):
                        team_task.append(TextChatMessage(content=message, source="user"))
                    elif isinstance(message, Image):
                        team_task.append(MultiModalMessage(source="user", content=[message]))
             

             
            # Run task with team
            team_result = await team.run(task=team_task, cancellation_token=cancellation_token)
            
            result = EvalRunResult(
                result=team_result,
                status=True,
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            
        except Exception as e:
            result = EvalRunResult(
                status=False,
                error=str(e),
                end_time=datetime.now()
            )
            
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation including team configuration."""
        data = super().to_dict()
        # Add team config
        data["team_config"] = self.team_config
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], team_manager):
        """Create from dictionary representation with provided team manager."""
        return cls(
            team_manager=team_manager,
            team_config=data.get("team_config", {}),
            name=data.get("name", "Team Runner"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )

 