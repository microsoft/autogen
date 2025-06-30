from typing import AsyncGenerator, Optional, Union

from autogen_core._component_config import ComponentModel
from autogen_core.models import SystemMessage
from autogen_core.tools._function_tool import FunctionToolConfig
from autogen_ext.models.openai import OpenAIChatCompletionClient
from pydantic import BaseModel

# Import tools to use as examples
from autogenstudio.gallery.tools import calculator_tool, fetch_webpage_tool


class ToolMakerEvent(BaseModel):
    """An event signaling a tool maker operation update."""

    status: str
    """The current status of tool generation (e.g., 'generating', 'testing', 'validating', 'complete', 'error')"""

    content: str
    """Description of what's happening"""


class ToolMaker:
    def __init__(self, model_client: Optional[OpenAIChatCompletionClient] = None):
        """
        Initialize the ToolMaker with a model client.

        Args:
            model_client: Optional model client. If not provided, uses GPT-4o.
        """
        self.model_client = model_client or OpenAIChatCompletionClient(
            model="gpt-4o",
            response_format=FunctionToolConfig,  # type: ignore[call-arg]
        )

    async def run(self, description: str) -> ComponentModel:
        """
        Generate a tool configuration based on a natural language description.

        Args:
            description: Natural language description of the tool's functionality

        Returns:
            ComponentModel: The generated tool configuration
        """
        # Generate tool config using model
        tool_config = await self._generate_tool_config(description)

        # Create and return the component model
        return ComponentModel(
            provider="autogen_core.tools.FunctionTool",
            component_type="tool",
            version=1,
            component_version=1,
            description=tool_config.description,
            label=tool_config.name,
            config=tool_config.model_dump(),
        )

    async def run_stream(self, description: str) -> AsyncGenerator[Union[ToolMakerEvent, ComponentModel], None]:
        """
        Generate a tool configuration based on a natural language description with streaming updates.

        Args:
            description: Natural language description of the tool's functionality

        Yields:
            ToolMakerEvent: Progress updates during tool generation
            ComponentModel: The final generated tool configuration
        """
        yield ToolMakerEvent(status="creating", content=f"Creating tool: {description}")

        tool_config = await self._generate_tool_config(description)

        component_model = ComponentModel(
            provider="autogen_core.tools.FunctionTool",
            component_type="tool",
            version=1,
            component_version=1,
            description=tool_config.description,
            label=tool_config.name,
            config=tool_config.model_dump(),
        )

        yield component_model

    async def _generate_tool_config(self, description: str) -> FunctionToolConfig:
        """
        Use model to generate a FunctionToolConfig.

        Args:
            description: Natural language description of the tool

        Returns:
            FunctionToolConfig: The generated tool configuration
        """
        # Get example tools as ComponentModels
        calculator_example = calculator_tool.dump_component()
        fetch_webpage_example = fetch_webpage_tool.dump_component()
        # generate_image_example = generate_image_tool.dump_component()

        prompt = f"""
        Create a FunctionTool configuration for the following tool description:
        {description}
        The configuration should include:
        1. A Python function with type annotations
        2. Required imports
        3. Function name and description
        4. Whether it supports cancellation
        Return the configuration in this format:
        {{
            "source_code": "def function_name(...): ...",
            "name": "function_name",
            "description": "Function description",
            "global_imports": [],
            "has_cancellation_support": false
        }}
        Here are examples of well-formed tool configurations:
        Example 1: Calculator Tool
        {calculator_example.config}
        Example 2: Fetch Webpage Tool
        {fetch_webpage_example.config}
        """

        # Get response from model
        response = await self.model_client.create(messages=[SystemMessage(content=prompt)])

        # Parse and validate the response
        try:
            assert isinstance(response.content, str)
            return FunctionToolConfig.model_validate_json(response.content)
        except Exception as e:
            raise ValueError(f"Failed to generate valid tool config: {str(e)}") from e
