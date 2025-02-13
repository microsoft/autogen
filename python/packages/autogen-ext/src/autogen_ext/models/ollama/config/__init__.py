from typing import Any, Mapping, Optional

from autogen_core.models import ModelCapabilities, ModelInfo  # type: ignore
from pydantic import BaseModel
from typing_extensions import TypedDict


class CreateArguments(TypedDict, total=False):
    model: str
    host: Optional[str]


class BaseOllamaClientConfiguration(CreateArguments, total=False):
    follow_redirects: bool
    timeout: Any
    headers: Optional[Mapping[str, str]]
    model_capabilities: ModelCapabilities  # type: ignore
    model_info: ModelInfo
    """What functionality the model supports, determined by default from model name but is overriden if value passed."""


# Pydantic equivalents of the above TypedDicts
class CreateArgumentsConfigModel(BaseModel):
    model: str
    host: str | None = None


class BaseOllamaClientConfigurationConfigModel(CreateArgumentsConfigModel):
    # Defaults for ollama.AsyncClient
    follow_redirects: bool = True
    timeout: Any = None
    headers: Mapping[str, str] | None = None
    model_capabilities: ModelCapabilities | None = None  # type: ignore
    model_info: ModelInfo | None = None
