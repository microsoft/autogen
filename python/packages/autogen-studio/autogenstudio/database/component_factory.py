import os
from pathlib import Path
from typing import List, Literal, Union, Optional, Dict, Any, Type
from datetime import datetime
import json
from autogen_agentchat.task import MaxMessageTermination, TextMentionTermination, StopMessageTermination
import yaml
import logging
from packaging import version

from ..datamodel import (
    TeamConfig, AgentConfig, ModelConfig, ToolConfig,
    TeamTypes, AgentTypes, ModelTypes, ToolTypes,
    ComponentType, ComponentConfig, ComponentConfigInput, TerminationConfig, TerminationTypes, Response
)
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool

logger = logging.getLogger(__name__)

# Type definitions for supported components
TeamComponent = Union[RoundRobinGroupChat, SelectorGroupChat]
AgentComponent = Union[AssistantAgent]  # Will grow with more agent types
# Will grow with more model types
ModelComponent = Union[OpenAIChatCompletionClient]
ToolComponent = Union[FunctionTool]  # Will grow with more tool types
TerminationComponent = Union[MaxMessageTermination,
                             StopMessageTermination, TextMentionTermination]

# Config type definitions

Component = Union[TeamComponent, AgentComponent, ModelComponent, ToolComponent]


ReturnType = Literal['object', 'dict', 'config']
Component = Union[RoundRobinGroupChat, SelectorGroupChat,
                  AssistantAgent, OpenAIChatCompletionClient, FunctionTool]


class ComponentFactory:
    """Creates and manages agent components with versioned configuration loading"""

    SUPPORTED_VERSIONS = {
        ComponentType.TEAM: ["1.0.0"],
        ComponentType.AGENT: ["1.0.0"],
        ComponentType.MODEL: ["1.0.0"],
        ComponentType.TOOL: ["1.0.0"],
        ComponentType.TERMINATION: ["1.0.0"]
    }

    def __init__(self):
        self._model_cache: Dict[str, OpenAIChatCompletionClient] = {}
        self._tool_cache: Dict[str, FunctionTool] = {}
        self._last_cache_clear = datetime.now()

    async def load(self, component: ComponentConfigInput, return_type: ReturnType = 'object') -> Union[Component, dict, ComponentConfig]:
        """
        Universal loader for any component type

        Args:
            component: Component configuration (file path, dict, or ComponentConfig)
            return_type: Type of return value ('object', 'dict', or 'config')

        Returns:
            Component instance, config dict, or ComponentConfig based on return_type

        Raises:
            ValueError: If component type is unknown or version unsupported
        """
        try:
            # Load and validate config
            if isinstance(component, (str, Path)):
                component_dict = await self._load_from_file(component)
                config = self._dict_to_config(component_dict)
            elif isinstance(component, dict):
                config = self._dict_to_config(component)
            else:
                config = component

            # Validate version
            if not self._is_version_supported(config.component_type, config.version):
                raise ValueError(
                    f"Unsupported version {config.version} for "
                    f"component type {config.component_type}. "
                    f"Supported versions: {self.SUPPORTED_VERSIONS[config.component_type]}"
                )

            # Return early if dict or config requested
            if return_type == 'dict':
                return config.model_dump()
            elif return_type == 'config':
                return config

            # Otherwise create and return component instance
            handlers = {
                ComponentType.TEAM: self.load_team,
                ComponentType.AGENT: self.load_agent,
                ComponentType.MODEL: self.load_model,
                ComponentType.TOOL: self.load_tool,
                ComponentType.TERMINATION: self.load_termination
            }

            handler = handlers.get(config.component_type)
            if not handler:
                raise ValueError(
                    f"Unknown component type: {config.component_type}")

            return await handler(config)

        except Exception as e:
            logger.error(f"Failed to load component: {str(e)}")
            raise

    async def load_directory(self, directory: Union[str, Path], check_exists: bool = False, return_type: ReturnType = 'object') -> List[Union[Component, dict, ComponentConfig]]:
        """
        Import all component configurations from a directory.
        """
        components = []
        try:
            directory = Path(directory)
            # Using Path.iterdir() instead of os.listdir
            for path in list(directory.glob("*")):
                if path.suffix.lower().endswith(('.json', '.yaml', '.yml')):
                    try:
                        component = await self.load(path, return_type)
                        components.append(component)
                    except Exception as e:
                        logger.info(
                            f"Failed to load component: {str(e)}, {path}")

            return components
        except Exception as e:
            logger.info(f"Failed to load directory: {str(e)}")
            return components

    def _dict_to_config(self, config_dict: dict) -> ComponentConfig:
        """Convert dictionary to appropriate config type based on component_type"""
        if "component_type" not in config_dict:
            raise ValueError("component_type is required in configuration")

        config_types = {
            ComponentType.TEAM: TeamConfig,
            ComponentType.AGENT: AgentConfig,
            ComponentType.MODEL: ModelConfig,
            ComponentType.TOOL: ToolConfig,
            ComponentType.TERMINATION: TerminationConfig  # Add mapping for termination
        }

        component_type = ComponentType(config_dict["component_type"])
        config_class = config_types.get(component_type)

        if not config_class:
            raise ValueError(f"Unknown component type: {component_type}")

        return config_class(**config_dict)

    async def load_termination(self, config: TerminationConfig) -> TerminationComponent:
        """Create termination condition instance from configuration."""
        try:
            if config.termination_type == TerminationTypes.MAX_MESSAGES:
                return MaxMessageTermination(max_messages=config.max_messages)
            elif config.termination_type == TerminationTypes.STOP_MESSAGE:
                return StopMessageTermination()
            elif config.termination_type == TerminationTypes.TEXT_MENTION:
                if not config.text:
                    raise ValueError(
                        "text parameter required for TextMentionTermination")
                return TextMentionTermination(text=config.text)
            else:
                raise ValueError(
                    f"Unsupported termination type: {config.termination_type}")
        except Exception as e:
            logger.error(f"Failed to create termination condition: {str(e)}")
            raise ValueError(
                f"Termination condition creation failed: {str(e)}")

    async def load_team(self, config: TeamConfig) -> TeamComponent:
        """Create team instance from configuration."""

        default_selector_prompt = """You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
"""
        try:
            # Load participants (agents)
            participants = []
            for participant in config.participants:
                agent = await self.load(participant)
                participants.append(agent)

            # Load model client if specified
            model_client = None
            if config.model_client:
                model_client = await self.load(config.model_client)

            # Load termination condition if specified
            termination = None
            if config.termination_condition:
                # Now we can use the universal load() method since termination is a proper component
                termination = await self.load(config.termination_condition)

            # Create team based on type
            if config.team_type == TeamTypes.ROUND_ROBIN:
                return RoundRobinGroupChat(
                    participants=participants,
                    termination_condition=termination
                )
            elif config.team_type == TeamTypes.SELECTOR:
                if not model_client:
                    raise ValueError(
                        "SelectorGroupChat requires a model_client")
                selector_prompt = config.selector_prompt if config.selector_prompt else default_selector_prompt
                return SelectorGroupChat(
                    participants=participants,
                    model_client=model_client,
                    termination_condition=termination,
                    selector_prompt=selector_prompt
                )
            else:
                raise ValueError(f"Unsupported team type: {config.team_type}")

        except Exception as e:
            logger.error(f"Failed to create team {config.name}: {str(e)}")
            raise ValueError(f"Team creation failed: {str(e)}")

    async def load_agent(self, config: AgentConfig) -> AgentComponent:
        """Create agent instance from configuration."""
        try:
            # Load model client if specified
            model_client = None
            if config.model_client:
                model_client = await self.load(config.model_client)
            system_message = config.system_message if config.system_message else "You are a helpful assistant"
            # Load tools if specified
            tools = []
            if config.tools:
                for tool_config in config.tools:
                    tool = await self.load(tool_config)
                    tools.append(tool)

            if config.agent_type == AgentTypes.ASSISTANT:
                return AssistantAgent(
                    name=config.name,
                    model_client=model_client,
                    tools=tools,
                    system_message=system_message
                )
            else:
                raise ValueError(
                    f"Unsupported agent type: {config.agent_type}")

        except Exception as e:
            logger.error(f"Failed to create agent {config.name}: {str(e)}")
            raise ValueError(f"Agent creation failed: {str(e)}")

    async def load_model(self, config: ModelConfig) -> ModelComponent:
        """Create model instance from configuration."""
        try:
            # Check cache first
            cache_key = str(config.model_dump())
            if cache_key in self._model_cache:
                logger.debug(f"Using cached model for {config.model}")
                return self._model_cache[cache_key]

            if config.model_type == ModelTypes.OPENAI:
                model = OpenAIChatCompletionClient(
                    model=config.model,
                    api_key=config.api_key,
                    base_url=config.base_url
                )
                self._model_cache[cache_key] = model
                return model
            else:
                raise ValueError(
                    f"Unsupported model type: {config.model_type}")

        except Exception as e:
            logger.error(f"Failed to create model {config.model}: {str(e)}")
            raise ValueError(f"Model creation failed: {str(e)}")

    async def load_tool(self, config: ToolConfig) -> ToolComponent:
        """Create tool instance from configuration."""
        try:
            # Validate required fields
            if not all([config.name, config.description, config.content, config.tool_type]):
                raise ValueError("Tool configuration missing required fields")

            # Check cache first
            cache_key = str(config.model_dump())
            if cache_key in self._tool_cache:
                logger.debug(f"Using cached tool '{config.name}'")
                return self._tool_cache[cache_key]

            if config.tool_type == ToolTypes.PYTHON_FUNCTION:
                tool = FunctionTool(
                    name=config.name,
                    description=config.description,
                    func=self._func_from_string(config.content)
                )
                self._tool_cache[cache_key] = tool
                return tool
            else:
                raise ValueError(f"Unsupported tool type: {config.tool_type}")

        except Exception as e:
            logger.error(f"Failed to create tool '{config.name}': {str(e)}")
            raise

    # Helper methods remain largely the same
    async def _load_from_file(self, path: Union[str, Path]) -> dict:
        """Load configuration from JSON or YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            with open(path) as f:
                if path.suffix == '.json':
                    return json.load(f)
                elif path.suffix in ('.yml', '.yaml'):
                    return yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported file format: {path.suffix}")
        except Exception as e:
            raise ValueError(f"Failed to load file {path}: {str(e)}")

    def _func_from_string(self, content: str) -> callable:
        """Convert function string to callable."""
        try:
            namespace = {}
            exec(content, namespace)
            for item in namespace.values():
                if callable(item) and not isinstance(item, type):
                    return item
            raise ValueError("No function found in provided code")
        except Exception as e:
            raise ValueError(f"Failed to create function: {str(e)}")

    def _is_version_supported(self, component_type: ComponentType, ver: str) -> bool:
        """Check if version is supported for component type."""
        try:
            v = version.parse(ver)
            return ver in self.SUPPORTED_VERSIONS[component_type]
        except version.InvalidVersion:
            return False

    async def cleanup(self) -> None:
        """Cleanup resources and clear caches."""
        for model in self._model_cache.values():
            if hasattr(model, 'cleanup'):
                await model.cleanup()

        for tool in self._tool_cache.values():
            if hasattr(tool, 'cleanup'):
                await tool.cleanup()

        self._model_cache.clear()
        self._tool_cache.clear()
        self._last_cache_clear = datetime.now()
        logger.info("Cleared all component caches")
