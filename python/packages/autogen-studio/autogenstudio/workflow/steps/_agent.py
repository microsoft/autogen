"""
Agent step for making OpenAI API calls in workflows.
"""

import asyncio
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import openai
import logging

from autogen_core import Component, ComponentBase

from ._step import BaseStep
from ..core._models import StepMetadata, Context

logger = logging.getLogger(__name__)


class AgentInput(BaseModel):
    """Input model for agent requests."""
    system_message: str = Field(description="System message for the agent")
    instruction: str = Field(description="User instruction/prompt")
    model: str = Field(default="gpt-4.1-nano", description="OpenAI model to use")
    temperature: float = Field(default=0.7, description="Model temperature (0.0-2.0)")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    context_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional context data")


class AgentOutput(BaseModel):
    """Output model for agent responses."""
    response: str = Field(description="Agent's response text")
    model_used: str = Field(description="Model that was used")
    tokens_used: Optional[int] = Field(default=None, description="Total tokens used")
    finish_reason: Optional[str] = Field(default=None, description="Reason for completion")
    cost_estimate: Optional[float] = Field(default=None, description="Estimated cost in USD")


class AgentStepConfig(BaseModel):
    """Configuration for AgentStep serialization."""
    step_id: str
    metadata: StepMetadata
    input_type_name: str
    output_type_name: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class AgentStep(Component[AgentStepConfig], BaseStep[AgentInput, AgentOutput]):
    """A step that makes OpenAI API calls."""
    
    component_config_schema = AgentStepConfig
    component_type = "step"
    component_provider_override = "autogenstudio.workflow.steps.AgentStep"
    
    def __init__(
        self,
        step_id: str,
        metadata: StepMetadata,
        input_type: type[AgentInput] = AgentInput,
        output_type: type[AgentOutput] = AgentOutput
    ):
        """Initialize the agent step.
        
        Args:
            step_id: Unique identifier for this step
            metadata: Step metadata
            input_type: Input validation model
            output_type: Output validation model
        """
        super().__init__(step_id, metadata, input_type, output_type)
    
    async def execute(self, input_data: AgentInput, context: Context) -> AgentOutput:
        """Execute the agent request.
        
        Args:
            input_data: Validated input data
            context: Additional context including workflow state
            
        Returns:
            Agent response data
            
        Raises:
            Exception: If API call fails
        """
        start_time = time.time()
        
        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": input_data.system_message},
                {"role": "user", "content": input_data.instruction}
            ]
            
            # Add context data if provided
            if input_data.context_data:
                context_content = f"\n\nContext data: {input_data.context_data}"
                messages[1]["content"] += context_content
            
            # Prepare API parameters
            api_params = {
                "model": input_data.model,
                "messages": messages,
                "temperature": input_data.temperature
            }
            
            if input_data.max_tokens:
                api_params["max_tokens"] = input_data.max_tokens
            
            # Make the API call
            logger.info(f"Making OpenAI API call with model {input_data.model}")
            client = openai.AsyncOpenAI()
            response = await client.chat.completions.create(**api_params)
            
            elapsed_time = time.time() - start_time
            
            # Extract response data
            choice = response.choices[0]
            usage = response.usage
            
            # Calculate cost estimate (rough approximation)
            cost_estimate = None
            if usage:
                # Rough cost estimates per 1K tokens (these vary by model)
                cost_per_1k_tokens = {
                    "gpt-4.1-nano": 0.00015,  # Example rate
                    "gpt-4": 0.03,
                    "gpt-3.5-turbo": 0.002,
                }
                model_cost = cost_per_1k_tokens.get(input_data.model, 0.01)
                cost_estimate = (usage.total_tokens / 1000) * model_cost
            
            # Store request info in context for debugging
            context.set(f'{self.step_id}_request_info', {
                'model': input_data.model,
                'temperature': input_data.temperature,
                'tokens_used': usage.total_tokens if usage else None,
                'elapsed_time': elapsed_time,
                'cost_estimate': cost_estimate
            })
            
            return AgentOutput(
                response=choice.message.content,
                model_used=input_data.model,
                tokens_used=usage.total_tokens if usage else None,
                finish_reason=choice.finish_reason,
                cost_estimate=cost_estimate
            )
            
        except openai.RateLimitError as e:
            elapsed_time = time.time() - start_time
            error_msg = f"OpenAI API rate limit exceeded: {str(e)}"
            logger.error(error_msg)
            context.set(f'{self.step_id}_error', {
                'type': 'rate_limit',
                'message': error_msg,
                'elapsed_time': elapsed_time
            })
            raise Exception(error_msg)
            
        except openai.AuthenticationError as e:
            elapsed_time = time.time() - start_time
            error_msg = f"OpenAI API authentication failed: {str(e)}"
            logger.error(error_msg)
            context.set(f'{self.step_id}_error', {
                'type': 'authentication_error',
                'message': error_msg,
                'elapsed_time': elapsed_time
            })
            raise Exception(error_msg)
            
        except openai.APIError as e:
            elapsed_time = time.time() - start_time
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg)
            context.set(f'{self.step_id}_error', {
                'type': 'api_error',
                'message': error_msg,
                'elapsed_time': elapsed_time
            })
            raise Exception(error_msg)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Unexpected error in agent step: {str(e)}"
            logger.error(error_msg)
            context.set(f'{self.step_id}_error', {
                'type': 'unexpected_error',
                'message': error_msg,
                'elapsed_time': elapsed_time
            })
            raise Exception(error_msg)
    
    def _to_config(self) -> AgentStepConfig:
        """Convert step to configuration for serialization."""
        base_data = self._serialize_types()
        return AgentStepConfig(**base_data)
    
    @classmethod
    def _from_config(cls, config: AgentStepConfig) -> "AgentStep":
        """Create step from configuration.
        
        Args:
            config: Step configuration
            
        Returns:
            Recreated AgentStep instance
        """
        input_type, output_type = cls._deserialize_types(config)
        return cls(
            step_id=config.step_id,
            metadata=config.metadata,
            input_type=input_type,
            output_type=output_type
        ) 