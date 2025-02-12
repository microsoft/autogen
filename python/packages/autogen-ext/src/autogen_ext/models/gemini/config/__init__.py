from typing import Dict, List, Literal, Optional, Union

from autogen_core.models import ModelInfo
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ResponseFormat(TypedDict):
    type: Literal["text", "json_object"]


class CreateArguments(TypedDict, total=False):
    temperature: Optional[float]
    top_p: Optional[float]
    top_k: Optional[int]
    max_output_tokens: Optional[int]
    stop_sequences: Optional[List[str]]
    candidate_count: Optional[int]
    safety_settings: Optional[Dict[str, Dict[str, str]]]


class BaseGeminiClientConfiguration(CreateArguments, total=False):
    model: str
    api_key: str
    timeout: Union[float, None]
    max_retries: int
    model_info: ModelInfo
    default_headers: Dict[str, str] | None


class GeminiClientConfiguration(BaseGeminiClientConfiguration, total=False):
    base_url: str  # Not used by the google-genai library, but kept for consistency


class VertexAIClientConfiguration(BaseGeminiClientConfiguration, total=False):
    project_id: str
    location: str
    credentials_path: Optional[str]

# Pydantic models for configuration
class CreateArgumentsConfigModel(BaseModel):
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_output_tokens: int | None = None
    stop_sequences: List[str] | None = None
    candidate_count: int | None = None
    safety_settings: Dict[str, Dict[str, str]] | None = None


class BaseGeminiClientConfigurationConfigModel(CreateArgumentsConfigModel):
    model: str
    api_key: str | None = None  # Optional, can be provided via environment variable
    timeout: float | None = None
    max_retries: int | None = 3
    model_info: ModelInfo | None = None  # This could be inferred
    default_headers: Dict[str, str] | None = None


class GeminiClientConfigurationConfigModel(BaseGeminiClientConfigurationConfigModel):
    base_url: str | None = None  # Not used by the google-genai library, but kept for consistency


class VertexAIClientConfigurationConfigModel(BaseGeminiClientConfigurationConfigModel):
    project_id: str
    location: str = "us-central1"  # Default location
    credentials_path: str | None = None  # Could also use ADC
