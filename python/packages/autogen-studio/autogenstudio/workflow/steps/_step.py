from abc import ABC, abstractmethod
from typing import Any, Dict, List, Generic, Optional, Type, Callable, Tuple
from pydantic import BaseModel, create_model
import asyncio
import logging
from datetime import datetime

from autogen_core import Component, ComponentBase

from ..core._models import InputType, OutputType, StepMetadata, StepStatus, Context

logger = logging.getLogger(__name__)


class BaseStepConfig(BaseModel):
    """Base configuration that all step configs must inherit from.
    
    Ensures UI compatibility by requiring type schema information.
    """
    step_id: str
    metadata: StepMetadata
    input_type_name: str
    output_type_name: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class BaseStep(ComponentBase[BaseStepConfig], Generic[InputType, OutputType]):
    """Base class for all workflow steps with automatic type serialization."""
    
    def __init__(
        self,
        step_id: str,
        metadata: StepMetadata,
        input_type: Type[InputType],
        output_type: Type[OutputType]
    ):
        """Initialize the step.
        
        Args:
            step_id: Unique identifier for this step
            metadata: Step metadata including name, description, etc.
            input_type: Pydantic model class for input validation
            output_type: Pydantic model class for output validation
        """
        self.step_id = step_id
        self.metadata = metadata
        self.input_type = input_type
        self.output_type = output_type
        self._status = StepStatus.PENDING
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._error: Optional[str] = None
    
    def _serialize_types(self) -> Dict[str, Any]:
        """Serialize input/output types to config data.
        
        Returns:
            Dictionary containing type names and schemas for serialization
        """
        return {
            "step_id": self.step_id,
            "metadata": self.metadata,
            "input_type_name": self.input_type.__name__,
            "output_type_name": self.output_type.__name__,
            "input_schema": self.input_type.model_json_schema(),
            "output_schema": self.output_type.model_json_schema()
        }
    
    @classmethod
    def _deserialize_types(cls, config: BaseStepConfig) -> Tuple[Type[InputType], Type[OutputType]]:
        """Deserialize input/output types from config data using Pydantic's create_model.
        
        Args:
            config: Step configuration with embedded schemas
            
        Returns:
            Tuple of (input_type, output_type) recreated from schemas
        """
        from typing import List, Dict, Any as AnyType
        
        def schema_to_field_definitions(schema: Dict[str, Any]) -> Dict[str, Any]:
            """Convert JSON schema to create_model field definitions."""
            from ..schema_utils import extract_primary_type_from_schema, get_python_type_from_json_schema_type
            
            properties = schema.get('properties', {})
            required_fields = set(schema.get('required', []))
            field_definitions = {}
            
            for field_name, field_schema in properties.items():
                json_type = extract_primary_type_from_schema(field_schema)
                python_type = get_python_type_from_json_schema_type(json_type)
                
                if field_name in required_fields:
                    # For required fields, use (type, ...) format
                    field_definitions[field_name] = (python_type, ...)
                else:
                    default_value = field_schema.get('default', None)
                    field_definitions[field_name] = (python_type, default_value)
            
            return field_definitions
        
        # Extract field definitions from schemas
        input_fields = schema_to_field_definitions(config.input_schema)
        output_fields = schema_to_field_definitions(config.output_schema)
        
        # Use create_model directly with the field definitions
        input_type = create_model(config.input_type_name, **input_fields)
        output_type = create_model(config.output_type_name, **output_fields)
        
        return input_type, output_type
    
    @property
    def status(self) -> StepStatus:
        """Get current step status."""
        return self._status
    
    @property
    def start_time(self) -> Optional[datetime]:
        """Get step start time."""
        return self._start_time
    
    @property
    def end_time(self) -> Optional[datetime]:
        """Get step end time."""
        return self._end_time
    
    @property
    def error(self) -> Optional[str]:
        """Get step error if any."""
        return self._error
    
    @property
    def duration(self) -> Optional[float]:
        """Get step duration in seconds."""
        if self._start_time and self._end_time:
            return (self._end_time - self._start_time).total_seconds()
        return None
    
    @abstractmethod
    async def execute(self, input_data: InputType, context: Context) -> OutputType:
        """Execute the step logic.
        
        Args:
            input_data: Validated input data
            context: Additional context including workflow state
            
        Returns:
            Validated output data
            
        Raises:
            Exception: If step execution fails
        """
        pass
    
    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Run the step with input validation and error handling.
        
        Args:
            input_data: Raw input data to validate
            context: Additional context including workflow state
            
        Returns:
            Dictionary containing output data
            
        Raises:
            Exception: If step execution fails after retries
        """
        logger.info(f"Starting step {self.step_id} ({self.metadata.name})")
        
        self._status = StepStatus.RUNNING
        self._start_time = datetime.now()
        self._error = None
        
        retry_count = 0
        max_retries = self.metadata.max_retries
        
        while retry_count <= max_retries:
            try:
                # Validate input
                validated_input = self.input_type(**input_data)
                
                # Create typed context from dict
                if isinstance(context, dict):
                    workflow_state = context.get('workflow_state', {})
                    # Use from_state_ref to avoid copying the state dict
                    typed_context = Context.from_state_ref(workflow_state)
                else:
                    typed_context = context
                
                # Execute with timeout if specified
                if self.metadata.timeout_seconds:
                    output = await asyncio.wait_for(
                        self.execute(validated_input, typed_context),
                        timeout=self.metadata.timeout_seconds
                    )
                else:
                    output = await self.execute(validated_input, typed_context)
                
                # Validate output
                if not isinstance(output, self.output_type):
                    if hasattr(output, 'model_dump'):
                        output = self.output_type(**output.model_dump())
                    elif isinstance(output, dict):
                        output = self.output_type(**output)
                    else:
                        # Try to convert to dict if possible
                        output = self.output_type(result=output)
                
                self._status = StepStatus.COMPLETED
                self._end_time = datetime.now()
                
                logger.info(f"Step {self.step_id} completed successfully in {self.duration:.2f}s")
                return output.model_dump()
                
            except asyncio.TimeoutError:
                error_msg = f"Step {self.step_id} timed out after {self.metadata.timeout_seconds}s"
                logger.error(error_msg)
                self._error = error_msg
                self._status = StepStatus.FAILED
                self._end_time = datetime.now()
                raise Exception(error_msg)
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Step {self.step_id} failed (attempt {retry_count}/{max_retries + 1}): {str(e)}"
                logger.error(error_msg)
                
                if retry_count <= max_retries:
                    logger.info(f"Retrying step {self.step_id} in 1 second...")
                    await asyncio.sleep(1)
                    continue
                else:
                    self._error = str(e)
                    self._status = StepStatus.FAILED
                    self._end_time = datetime.now()
                    raise
        
        # Should never reach here
        raise Exception(f"Unexpected error in step {self.step_id}")
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data against the input schema.
        
        Args:
            data: Input data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self.input_type(**data)
            return True
        except Exception:
            return False
    
    def validate_output(self, data: Dict[str, Any]) -> bool:
        """Validate output data against the output schema.
        
        Args:
            data: Output data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self.output_type(**data)
            return True
        except Exception:
            return False
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the input/output schema for this step.
        
        Returns:
            Dictionary containing input and output schemas
        """
        return {
            "step_id": self.step_id,
            "metadata": self.metadata.model_dump(),
            "input_type": self.input_type.__name__,
            "output_type": self.output_type.__name__,
            "input_schema": self.input_type.model_json_schema(),
            "output_schema": self.output_type.model_json_schema()
        }


class FunctionStepConfig(BaseStepConfig):
    """Configuration for FunctionStep serialization."""
    # Base fields inherited: step_id, metadata, input_type_name, output_type_name, input_schema, output_schema
    # Note: We can't easily serialize functions, so we'll store a reference
    function_name: Optional[str] = None
    function_module: Optional[str] = None


class FunctionStep(Component[FunctionStepConfig], BaseStep[InputType, OutputType]):
    """A step that executes a function as its core operation."""
    
    component_config_schema = FunctionStepConfig
    component_type = "step"
    component_provider_override = "autogenstudio.workflow.steps.FunctionStep"
    
    
    def __init__(
        self,
        step_id: str,
        metadata: StepMetadata,
        input_type: Type[InputType],
        output_type: Type[OutputType],
        func: Callable
    ):
        """Initialize with a function to execute.
        
        Args:
            step_id: Unique identifier for this step
            metadata: Step metadata
            input_type: Input validation model
            output_type: Output validation model
            func: Function to execute (can be sync or async)
        """
        super().__init__(step_id, metadata, input_type, output_type)
        self.func = func
    
    async def execute(self, input_data: InputType, context: Context) -> OutputType:
        """Execute the wrapped function.
        
        Args:
            input_data: Validated input data
            context: Additional context
            
        Returns:
            Function output
        """
        if asyncio.iscoroutinefunction(self.func):
            result = await self.func(input_data, context)
        else:
            result = self.func(input_data, context)
        
        if isinstance(result, dict):
            return self.output_type(**result)
        elif hasattr(result, 'dict'):
            return result
        else:
            # Assume it's a simple value that can be wrapped
            return self.output_type(result=result)
    
    def _to_config(self) -> FunctionStepConfig:
        """Convert step to configuration for serialization."""
        func_name = None
        func_module = None
        
        if hasattr(self.func, '__name__'):
            func_name = self.func.__name__
        if hasattr(self.func, '__module__'):
            func_module = self.func.__module__
        
        # Get base type serialization data
        base_data = self._serialize_types()
        
        return FunctionStepConfig(
            **base_data,
            function_name=func_name,
            function_module=func_module
        )
    
    @classmethod 
    def _from_config(cls, config: FunctionStepConfig) -> "FunctionStep":
        """Create step from configuration.
        
        Args:
            config: Step configuration
            
        Note:
            This basic implementation cannot recreate the function.
            In practice, you'd need a function registry or other mechanism
            to deserialize callable functions.
        """
        raise NotImplementedError(
            "FunctionStep deserialization is not fully supported as functions "
            "cannot be easily serialized. Consider using a function registry "
            "or other mechanism for this use case."
        )



class EchoStepConfig(BaseStepConfig):
    """Configuration for EchoStep serialization."""
    # Base fields inherited: step_id, metadata, input_type_name, output_type_name, input_schema, output_schema
    prefix: str = "Echo: "
    suffix: str = ""
    delay_seconds: float = 3  # Optional delay for testing/demo


class EchoStep(Component[EchoStepConfig], BaseStep[InputType, OutputType]):
    """A simple step that echoes input with prefix/suffix - fully serializable."""

    component_config_schema = EchoStepConfig
    component_type = "step"
    component_provider_override = "autogenstudio.workflow.steps.EchoStep"

    def __init__(
        self,
        step_id: str,
        metadata: StepMetadata,
        input_type: Type[InputType],
        output_type: Type[OutputType],
        prefix: str = "Echo: ",
        suffix: str = "",
        delay_seconds: float = 0.0
    ):
        """Initialize the echo step.
        
        Args:
            step_id: Unique identifier for this step
            metadata: Step metadata
            input_type: Pydantic model class for input validation
            output_type: Pydantic model class for output validation
            prefix: String to prepend to input
            suffix: String to append to input
            delay_seconds: Optional delay for testing/demo
        """
        super().__init__(step_id, metadata, input_type, output_type)
        self.prefix = prefix
        self.suffix = suffix
        self.delay_seconds = delay_seconds
    
    async def execute(self, input_data: InputType, context: Context) -> OutputType:
        """Execute the echo operation, with optional delay for testing/demo."""
        # Optional delay for testing/demo
        if self.delay_seconds and self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        # Try to get the message from different possible field names
        message = None

        # Try common field names
        for field_name in ['message', 'result', 'text', 'content', 'data']:
            if hasattr(input_data, field_name):
                message = getattr(input_data, field_name)
                break

        # If no common field found, try the first field
        if message is None:
            field_names = list(input_data.model_fields.keys())
            if field_names:
                message = getattr(input_data, field_names[0])
            else:
                # Fall back to string representation
                message = str(input_data)

        result = f"{self.prefix}{message}{self.suffix}"

        # Store echo operation in context
        context.set(f'{self.step_id}_echo_info', {
            'original': message,
            'prefix': self.prefix,
            'suffix': self.suffix,
            'result': result
        })

        # Create output - try different field names
        output_fields = list(self.output_type.model_fields.keys())
        if 'result' in output_fields:
            return self.output_type(result=result)
        elif 'message' in output_fields:
            return self.output_type(message=result)
        elif 'text' in output_fields:
            return self.output_type(text=result)
        elif 'response' in output_fields:
            return self.output_type(response=result)
        elif 'content' in output_fields:
            return self.output_type(content=result)
        else:
            # Fall back to first field
            field_name = output_fields[0]
            return self.output_type(**{field_name: result})
    
    def _to_config(self) -> EchoStepConfig:
        """Convert step to configuration for serialization."""
        # Get base type serialization data
        base_data = self._serialize_types()
        return EchoStepConfig(
            **base_data,
            prefix=self.prefix,
            suffix=self.suffix,
            delay_seconds=self.delay_seconds
        )
    
    @classmethod
    def _from_config(cls, config: EchoStepConfig) -> "EchoStep":
        """Create step from configuration using shared schema-based deserialization.
        Args:
            config: Step configuration with embedded schemas
        Returns:
            Recreated EchoStep instance with dynamically created types
        """
        # Use shared type deserialization
        input_type, output_type = cls._deserialize_types(config)
        return cls(
            step_id=config.step_id,
            metadata=config.metadata,
            input_type=input_type,
            output_type=output_type,
            prefix=config.prefix,
            suffix=config.suffix,
            delay_seconds=getattr(config, 'delay_seconds', 0.0)
        )




