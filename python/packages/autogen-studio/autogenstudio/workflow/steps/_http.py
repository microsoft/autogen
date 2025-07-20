"""
HTTP step for making web requests in workflows.
"""

import asyncio
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import requests
import logging

from autogen_core import Component, ComponentBase

from ._step import BaseStep
from ..core._models import StepMetadata, Context

logger = logging.getLogger(__name__)


class HttpRequestInput(BaseModel):
    """Input model for HTTP requests."""
    url: str = Field(description="URL to fetch")
    method: str = Field(default="GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Request data for POST/PUT")
    timeout: Optional[int] = Field(default=30, description="Request timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Whether to verify SSL certificates")


class HttpResponseOutput(BaseModel):
    """Output model for HTTP responses."""
    status_code: int = Field(description="HTTP status code")
    content: str = Field(description="Response content as string")
    headers: Dict[str, str] = Field(description="Response headers")
    url: str = Field(description="Final URL after redirects")
    encoding: Optional[str] = Field(default=None, description="Response encoding")
    elapsed_time: float = Field(description="Request duration in seconds")


class HttpStepConfig(BaseModel):
    """Configuration for HttpStep serialization."""
    step_id: str
    metadata: StepMetadata
    input_type_name: str
    output_type_name: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class HttpStep(Component[HttpStepConfig], BaseStep[HttpRequestInput, HttpResponseOutput]):
    """A step that makes HTTP requests and returns the response."""
    
    component_config_schema = HttpStepConfig
    component_type = "step"
    component_provider_override = "autogenstudio.workflow.steps.HttpStep"
    
    def __init__(
        self,
        step_id: str,
        metadata: StepMetadata,
        input_type: type[HttpRequestInput] = HttpRequestInput,
        output_type: type[HttpResponseOutput] = HttpResponseOutput
    ):
        """Initialize the HTTP step.
        
        Args:
            step_id: Unique identifier for this step
            metadata: Step metadata
            input_type: Input validation model
            output_type: Output validation model
        """
        super().__init__(step_id, metadata, input_type, output_type)
    
    async def execute(self, input_data: HttpRequestInput, context: Context) -> HttpResponseOutput:
        """Execute the HTTP request.
        
        Args:
            input_data: Validated input data
            context: Additional context including workflow state
            
        Returns:
            HTTP response data
            
        Raises:
            Exception: If HTTP request fails
        """
        start_time = time.time()
        
        try:
            # Prepare request parameters
            request_kwargs = {
                'timeout': input_data.timeout,
                'verify': input_data.verify_ssl
            }
            
            if input_data.headers:
                request_kwargs['headers'] = input_data.headers
            
            if input_data.data and input_data.method.upper() in ['POST', 'PUT', 'PATCH']:
                request_kwargs['json'] = input_data.data
            
            # Make the request
            logger.info(f"Making {input_data.method} request to {input_data.url}")
            response = requests.request(
                method=input_data.method.upper(),
                url=input_data.url,
                **request_kwargs
            )
            
            elapsed_time = time.time() - start_time
            
            # Store request info in context for debugging
            context.set(f'{self.step_id}_request_info', {
                'url': input_data.url,
                'method': input_data.method,
                'status_code': response.status_code,
                'elapsed_time': elapsed_time,
                'content_length': len(response.content)
            })
            
            # Handle HTTP errors
            response.raise_for_status()
            
            # Determine encoding
            encoding = response.encoding
            if not encoding:
                encoding = response.apparent_encoding
            
            # Decode content
            try:
                content = response.text
            except UnicodeDecodeError:
                # Fallback to raw content if text decoding fails
                content = response.content.decode('utf-8', errors='replace')
            
            return HttpResponseOutput(
                status_code=response.status_code,
                content=content,
                headers=dict(response.headers),
                url=response.url,
                encoding=encoding,
                elapsed_time=elapsed_time
            )
            
        except requests.exceptions.Timeout:
            elapsed_time = time.time() - start_time
            error_msg = f"Request to {input_data.url} timed out after {input_data.timeout} seconds"
            logger.error(error_msg)
            context.set(f'{self.step_id}_error', {
                'type': 'timeout',
                'message': error_msg,
                'elapsed_time': elapsed_time
            })
            raise Exception(error_msg)
            
        except requests.exceptions.SSLError as e:
            elapsed_time = time.time() - start_time
            error_msg = f"SSL error for {input_data.url}: {str(e)}"
            logger.error(error_msg)
            context.set(f'{self.step_id}_error', {
                'type': 'ssl_error',
                'message': error_msg,
                'elapsed_time': elapsed_time
            })
            raise Exception(error_msg)
            
        except requests.exceptions.RequestException as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Request failed for {input_data.url}: {str(e)}"
            logger.error(error_msg)
            context.set(f'{self.step_id}_error', {
                'type': 'request_error',
                'message': error_msg,
                'elapsed_time': elapsed_time
            })
            raise Exception(error_msg)
    
    def _to_config(self) -> HttpStepConfig:
        """Convert step to configuration for serialization."""
        base_data = self._serialize_types()
        return HttpStepConfig(**base_data)
    
    @classmethod
    def _from_config(cls, config: HttpStepConfig) -> "HttpStep":
        """Create step from configuration.
        
        Args:
            config: Step configuration
            
        Returns:
            Recreated HttpStep instance
        """
        input_type, output_type = cls._deserialize_types(config)
        return cls(
            step_id=config.step_id,
            metadata=config.metadata,
            input_type=input_type,
            output_type=output_type
        ) 