from typing import Any, Mapping, Optional, Union

from autogen_core.models import ModelCapabilities, ModelInfo  # type: ignore
from ollama import Options
from pydantic import BaseModel
from typing_extensions import TypedDict


# response_format MUST be a pydantic.BaseModel type or None
# TODO: check if we can extend response_format to support json and/or dict
# TODO: extend arguments to all AsyncClient supported args
class CreateArguments(TypedDict, total=False):
    model: str
    host: Optional[str]
    response_format: Any


class BaseOllamaClientConfiguration(CreateArguments, total=False):
    follow_redirects: bool
    timeout: Any
    headers: Optional[Mapping[str, str]]
    model_capabilities: ModelCapabilities  # type: ignore
    model_info: ModelInfo
    """What functionality the model supports, determined by default from model name but is overriden if value passed."""
    options: Optional[Union[Mapping[str, Any], Options]]


# Pydantic equivalents of the above TypedDicts
# response_format MUST be a pydantic.BaseModel type or None
class CreateArgumentsConfigModel(BaseModel):
    model: str
    host: str | None = None
    response_format: Any = None


class BaseOllamaClientConfigurationConfigModel(CreateArgumentsConfigModel):
    # Defaults for ollama.AsyncClient
    follow_redirects: bool = True
    timeout: Any = None
    headers: Mapping[str, str] | None = None
    model_capabilities: ModelCapabilities | None = None  # type: ignore
    model_info: ModelInfo | None = None
    options: Mapping[str, Any] | Options | None = None
