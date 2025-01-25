import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Union

import aiofiles
import yaml
from autogen_core import Component, ComponentBase, ComponentModel
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import Tool

from ..datamodel.types import (
    ComponentConfigInput,
)

logger = logging.getLogger(__name__)

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

    def __init__(self):
        self._model_cache: Dict[str, ChatCompletionClient] = {}
        self._tool_cache: Dict[str, Tool] = {}
        self._last_cache_clear = datetime.now()

    async def load(
        self, component: ComponentConfigInput, input_func: Optional[Callable] = None, return_type: ReturnType = "object"
    ) -> Union[Component, dict]:
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
                config = ComponentBase.load_component(component_dict)
            elif isinstance(component, dict) or isinstance(component, ComponentModel):
                config = ComponentBase.load_component(component)
            else:
                config = component

            # Return early if dict or config requested
            if return_type == "dict":
                return json.loads(config.dump_component().model_dump_json())

            return config

        except Exception as e:
            logger.error(f"Failed to load component: {str(e)}")
            raise

    async def load_directory(
        self, directory: Union[str, Path], return_type: ReturnType = "object"
    ) -> List[Union[Component, dict]]:
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
