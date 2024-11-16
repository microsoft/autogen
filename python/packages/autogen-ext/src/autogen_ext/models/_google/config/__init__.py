from typing import TypedDict, Optional, Sequence
from autogen_core.components.tools import Tool
from google.generativeai.types import safety_types
from google.generativeai.types import generation_types
from google.generativeai.types import content_types


class GeminiClientConfiguration(TypedDict, total=False):
    model: Optional[str]
    api_key: Optional[str]
    safety_settings: Optional[safety_types.SafetySettingOptions]
    generation_config: Optional[generation_types.GenerationConfigType]
    tools: Optional[Sequence[Tool]]
    tool_config: Optional[content_types.ToolConfigType]
    system_instruction: Optional[content_types.ContentType]
