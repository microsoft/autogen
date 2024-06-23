from __future__ import annotations

import copy
import inspect
import json
import os
import time
import warnings
from typing import Any, Dict, List, Tuple, Union

from cohere import Client as Cohere
from cohere.types import ChatMessage, ToolCallDelta
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage
from typing_extensions import Annotated

from autogen.oai.client_utils import validate_parameter

COHERE_PRICING_1K = {
    "command-r-plus": (0.003, 0.015),
    "command-r": (0.0005, 0.0015),
    "command-nightly": (0.00025, 0.00125),
    "command": (0.015, 0.075),
    "command-light": (0.008, 0.024),
    "ccommand-light-nightly": (0.008, 0.024),
}


class CohereClient:
    def __init__(self, **kwargs):
        self.api_key = kwargs.get("api_key", None)

        if not self.api_key:
            self.api_key = os.getenv("COHERE_API_KEY")

        if not self.api_key:
            raise ValueError("API key is required")

        self.client = Cohere(self.api_key)
        self.last_tool_use_status = {}

    @property
    def api_key(self) -> str:
        return self.api_key
