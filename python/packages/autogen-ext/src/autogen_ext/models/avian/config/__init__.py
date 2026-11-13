from typing import Dict, List, Literal, Optional, Union

from autogen_core.models import ModelCapabilities, ModelInfo  # type: ignore
from pydantic import BaseModel, SecretStr
from typing_extensions import Required, TypedDict


class CreateArguments(TypedDict, total=False):
    frequency_penalty: Optional[float]
    max_tokens: Optional[int]
    presence_penalty: Optional[float]
    seed: Optional[int]
    stop: Union[Optional[str], List[str]]
    temperature: Optional[float]
    top_p: Optional[float]


class AvianClientConfiguration(CreateArguments, total=False):
    model: Required[str]
    api_key: str
    base_url: str
    timeout: Union[float, None]
    max_retries: int
    model_capabilities: ModelCapabilities  # type: ignore
    model_info: ModelInfo


class CreateArgumentsConfigModel(BaseModel):
    frequency_penalty: float | None = None
    max_tokens: int | None = None
    presence_penalty: float | None = None
    seed: int | None = None
    stop: str | List[str] | None = None
    temperature: float | None = None
    top_p: float | None = None


class AvianClientConfigurationConfigModel(CreateArgumentsConfigModel):
    model: str
    api_key: SecretStr | None = None
    base_url: str | None = None
    timeout: float | None = None
    max_retries: int | None = None
    model_capabilities: ModelCapabilities | None = None  # type: ignore
    model_info: ModelInfo | None = None
