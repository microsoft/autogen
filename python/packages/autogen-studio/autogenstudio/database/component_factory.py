import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Union

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import (
    ExternalTermination,
    HandoffTermination,
    MaxMessageTermination,
    SourceMatchTermination,
    StopMessageTermination,
    TextMentionTermination,
    TimeoutTermination,
    TokenUsageTermination,
)
from autogen_agentchat.teams import MagenticOneGroupChat, RoundRobinGroupChat, SelectorGroupChat
from autogen_core.components.tools import FunctionTool
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.models import OpenAIChatCompletionClient

from ..datamodel.types import (
    AgentConfig,
    AgentTypes,
    ComponentConfig,
    ComponentConfigInput,
    ComponentTypes,
    ModelConfig,
    ModelTypes,
    TeamConfig,
    TeamTypes,
    TerminationConfig,
    TerminationTypes,
    ToolConfig,
    ToolTypes,
)
from ..utils.utils import Version

logger = logging.getLogger(__name__)

TeamComponent = Union[RoundRobinGroupChat, SelectorGroupChat, MagenticOneGroupChat]
AgentComponent = Union[AssistantAgent, MultimodalWebSurfer, UserProxyAgent, FileSurfer, MagenticOneCoderAgent]
ModelComponent = Union[OpenAIChatCompletionClient]
ToolComponent = Union[FunctionTool]  # Will grow with more tool types
TerminationComponent = Union[
    MaxMessageTermination,
    StopMessageTermination,
    TextMentionTermination,
    TimeoutTermination,
    ExternalTermination,
    TokenUsageTermination,
    HandoffTermination,
    SourceMatchTermination,
    StopMessageTermination,
]

Component = Union[TeamComponent, AgentComponent, ModelComponent, ToolComponent, TerminationComponent]

ReturnType = Literal["object", "dict", "config"]

DEFAULT_SELECTOR_PROMPT = """You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
"""

CONFIG_RETURN_TYPES = Literal["object", "dict", "config"]


class ComponentFactory:
    """Creates and manages agent components with versioned configuration loading"""

    SUPPORTED_VERSIONS = {
        ComponentTypes.TEAM: ["1.0.0"],
        ComponentTypes.AGENT: ["1.0.0"],
        ComponentTypes.MODEL: ["1.0.0"],
        ComponentTypes.TOOL: ["1.0.0"],
        ComponentTypes.TERMINATION: ["1.0.0"],
    }

    def __init__(self):
        self._model_cache: Dict[str, OpenAIChatCompletionClient] = {}
        self._tool_cache: Dict[str, FunctionTool] = {}
        self._last_cache_clear = datetime.now()

    async def load(
        self, component: ComponentConfigInput, input_func: Optional[Callable] = None, return_type: ReturnType = "object"
    ) -> Union[Component, dict, ComponentConfig]:
        """
        Universal loader for any component type

        Args:
            component: Component configuration (file path, dict, or ComponentConfig)
            input_func: Optional callable for user input handling
            return_type: Type of return value ('object', 'dict', or 'config')

        Returns:
            Component instance, config dict, or ComponentConfig based on return_type
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
            if return_type == "dict":
                return config.model_dump()
            elif return_type == "config":
                return config

            # Otherwise create and return component instance
            handlers = {
                ComponentTypes.TEAM: lambda c: self.load_team(c, input_func),
                ComponentTypes.AGENT: lambda c: self.load_agent(c, input_func),
                ComponentTypes.MODEL: self.load_model,
                ComponentTypes.TOOL: self.load_tool,
                ComponentTypes.TERMINATION: self.load_termination,
            }

            handler = handlers.get(config.component_type)
            if not handler:
                raise ValueError(f"Unknown component type: {config.component_type}")

            return await handler(config)

        except Exception as e:
            logger.error(f"Failed to load component: {str(e)}")
            raise

    async def load_directory(
        self, directory: Union[str, Path], return_type: ReturnType = "object"
    ) -> List[Union[Component, dict, ComponentConfig]]:
        """
        Import all component configurations from a directory.
        """
        components = []
        try:
            directory = Path(directory)
            # Using Path.iterdir() instead of os.listdir
            for path in list(directory.glob("*")):
                if path.suffix.lower().endswith((".json", ".yaml", ".yml")):
                    try:
                        component = await self.load(path, return_type=return_type)
                        components.append(component)
                    except Exception as e:
                        logger.info(f"Failed to load component: {str(e)}, {path}")

            return components
        except Exception as e:
            logger.info(f"Failed to load directory: {str(e)}")
            return components

    def _dict_to_config(self, config_dict: dict) -> ComponentConfig:
        """Convert dictionary to appropriate config type based on component_type"""
        if "component_type" not in config_dict:
            raise ValueError("component_type is required in configuration")

        config_types = {
            ComponentTypes.TEAM: TeamConfig,
            ComponentTypes.AGENT: AgentConfig,
            ComponentTypes.MODEL: ModelConfig,
            ComponentTypes.TOOL: ToolConfig,
            ComponentTypes.TERMINATION: TerminationConfig,  # Add mapping for termination
        }

        component_type = ComponentTypes(config_dict["component_type"])
        config_class = config_types.get(component_type)

        if not config_class:
            raise ValueError(f"Unknown component type: {component_type}")

        return config_class(**config_dict)

    async def load_termination(self, config: TerminationConfig) -> TerminationComponent:
        """Create termination condition instance from configuration."""
        try:
            if config.termination_type == TerminationTypes.COMBINATION:
                if not config.conditions or len(config.conditions) < 2:
                    raise ValueError("Combination termination requires at least 2 conditions")
                if not config.operator:
                    raise ValueError("Combination termination requires an operator (and/or)")

                # Load first two conditions
                conditions = [await self.load_termination(cond) for cond in config.conditions[:2]]
                result = conditions[0] & conditions[1] if config.operator == "and" else conditions[0] | conditions[1]

                # Process remaining conditions if any
                for condition in config.conditions[2:]:
                    next_condition = await self.load_termination(condition)
                    result = result & next_condition if config.operator == "and" else result | next_condition

                return result

            elif config.termination_type == TerminationTypes.MAX_MESSAGES:
                if config.max_messages is None:
                    raise ValueError("max_messages parameter required for MaxMessageTermination")
                return MaxMessageTermination(max_messages=config.max_messages)

            elif config.termination_type == TerminationTypes.STOP_MESSAGE:
                return StopMessageTermination()

            elif config.termination_type == TerminationTypes.TEXT_MENTION:
                if not config.text:
                    raise ValueError("text parameter required for TextMentionTermination")
                return TextMentionTermination(text=config.text)

            else:
                raise ValueError(f"Unsupported termination type: {config.termination_type}")

        except Exception as e:
            logger.error(f"Failed to create termination condition: {str(e)}")
            raise ValueError(f"Termination condition creation failed: {str(e)}") from e

    async def load_team(self, config: TeamConfig, input_func: Optional[Callable] = None) -> TeamComponent:
        """Create team instance from configuration."""
        try:
            # Load participants (agents) with input_func
            participants = []
            for participant in config.participants:
                agent = await self.load(participant, input_func=input_func)
                participants.append(agent)

            # Load model client if specified
            model_client = None
            if config.model_client:
                model_client = await self.load(config.model_client)

            # Load termination condition if specified
            termination = None
            if config.termination_condition:
                termination = await self.load(config.termination_condition)

            # Create team based on type
            if config.team_type == TeamTypes.ROUND_ROBIN:
                return RoundRobinGroupChat(participants=participants, termination_condition=termination)
            elif config.team_type == TeamTypes.SELECTOR:
                if not model_client:
                    raise ValueError("SelectorGroupChat requires a model_client")
                selector_prompt = config.selector_prompt if config.selector_prompt else DEFAULT_SELECTOR_PROMPT
                return SelectorGroupChat(
                    participants=participants,
                    model_client=model_client,
                    termination_condition=termination,
                    selector_prompt=selector_prompt,
                )
            elif config.team_type == TeamTypes.MAGENTIC_ONE:
                if not model_client:
                    raise ValueError("MagenticOneGroupChat requires a model_client")
                return MagenticOneGroupChat(
                    participants=participants,
                    model_client=model_client,
                    termination_condition=termination if termination is not None else None,
                    max_turns=config.max_turns if config.max_turns is not None else 20,
                )
            else:
                raise ValueError(f"Unsupported team type: {config.team_type}")

        except Exception as e:
            logger.error(f"Failed to create team {config.name}: {str(e)}")
            raise ValueError(f"Team creation failed: {str(e)}") from e

    async def load_agent(self, config: AgentConfig, input_func: Optional[Callable] = None) -> AgentComponent:
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

            if config.agent_type == AgentTypes.USERPROXY:
                return UserProxyAgent(
                    name=config.name,
                    description=config.description or "A human user",
                    input_func=input_func,  # Pass through to UserProxyAgent
                )
            elif config.agent_type == AgentTypes.ASSISTANT:
                return AssistantAgent(
                    name=config.name,
                    description=config.description or "A helpful assistant",
                    model_client=model_client,
                    tools=tools,
                    system_message=system_message,
                )
            elif config.agent_type == AgentTypes.MULTIMODAL_WEBSURFER:
                return MultimodalWebSurfer(
                    name=config.name,
                    model_client=model_client,
                    headless=config.headless if config.headless is not None else True,
                    debug_dir=config.logs_dir if config.logs_dir is not None else "logs",
                    downloads_folder=config.logs_dir if config.logs_dir is not None else "logs",
                    to_save_screenshots=config.to_save_screenshots if config.to_save_screenshots is not None else False,
                    use_ocr=config.use_ocr if config.use_ocr is not None else False,
                    animate_actions=config.animate_actions if config.animate_actions is not None else False,
                )
            elif config.agent_type == AgentTypes.FILE_SURFER:
                return FileSurfer(
                    name=config.name,
                    model_client=model_client,
                )
            elif config.agent_type == AgentTypes.MAGENTIC_ONE_CODER:
                return MagenticOneCoderAgent(
                    name=config.name,
                    model_client=model_client,
                )
            else:
                raise ValueError(f"Unsupported agent type: {config.agent_type}")

        except Exception as e:
            logger.error(f"Failed to create agent {config.name}: {str(e)}")
            raise ValueError(f"Agent creation failed: {str(e)}") from e

    async def load_model(self, config: ModelConfig) -> ModelComponent:
        """Create model instance from configuration."""
        try:
            # Check cache first
            cache_key = str(config.model_dump())
            if cache_key in self._model_cache:
                logger.debug(f"Using cached model for {config.model}")
                return self._model_cache[cache_key]

            if config.model_type == ModelTypes.OPENAI:
                model = OpenAIChatCompletionClient(model=config.model, api_key=config.api_key, base_url=config.base_url)
                self._model_cache[cache_key] = model
                return model
            else:
                raise ValueError(f"Unsupported model type: {config.model_type}")

        except Exception as e:
            logger.error(f"Failed to create model {config.model}: {str(e)}")
            raise ValueError(f"Model creation failed: {str(e)}") from e

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
                    name=config.name, description=config.description, func=self._func_from_string(config.content)
                )
                self._tool_cache[cache_key] = tool
                return tool
            else:
                raise ValueError(f"Unsupported tool type: {config.tool_type}")

        except Exception as e:
            logger.error(f"Failed to create tool '{config.name}': {str(e)}")
            raise

    async def _load_from_file(self, path: Union[str, Path]) -> dict:
        """Load configuration from JSON or YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            async with aiofiles.open(path) as f:
                content = await f.read()
                if path.suffix == ".json":
                    return json.loads(content)
                elif path.suffix in (".yml", ".yaml"):
                    return yaml.safe_load(content)
                else:
                    raise ValueError(f"Unsupported file format: {path.suffix}")
        except Exception as e:
            raise ValueError(f"Failed to load file {path}: {str(e)}") from e

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
            raise ValueError(f"Failed to create function: {str(e)}") from e

    def _is_version_supported(self, component_type: ComponentTypes, ver: str) -> bool:
        """Check if version is supported for component type."""
        try:
            version = Version(ver)
            supported = [Version(v) for v in self.SUPPORTED_VERSIONS[component_type]]
            return any(version == v for v in supported)
        except ValueError:
            return False

    async def cleanup(self) -> None:
        """Cleanup resources and clear caches."""
        for model in self._model_cache.values():
            if hasattr(model, "cleanup"):
                await model.cleanup()

        for tool in self._tool_cache.values():
            if hasattr(tool, "cleanup"):
                await tool.cleanup()

        self._model_cache.clear()
        self._tool_cache.clear()
        self._last_cache_clear = datetime.now()
        logger.info("Cleared all component caches")
