import json
import logging
from pathlib import Path
from typing import Union

import aiofiles
import yaml

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages loading tool configs from file/folder to populate the DB."""

    @staticmethod
    async def load_from_file(path: Union[str, Path]) -> dict:
        """Load tool configuration from JSON/YAML file"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        async with aiofiles.open(path) as f:
            content = await f.read()
            if path.suffix == ".json":
                return json.loads(content)
            elif path.suffix in (".yml", ".yaml"):
                return yaml.safe_load(content)
            raise ValueError(f"Unsupported file format: {path.suffix}")
