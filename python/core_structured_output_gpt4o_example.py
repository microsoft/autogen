"""
Structured Output with GPT-4o Models (Azure OpenAI)

This example demonstrates how to obtain structured output using GPT-4o models and Pydantic, and how to track LLM usage with a logger.

Requirements:
- pip install pydantic autogen-core autogen-ext azure-identity
- Azure OpenAI deployment with gpt-4o-2024-08-06

Run with: python python/core_structured_output_gpt4o_example.py
"""
import json
import os
import logging
from typing import Optional
from pydantic import BaseModel

from autogen_core.models import UserMessage
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_core.logging import LLMCallEvent
from autogen_core import EVENT_LOGGER_NAME

# ------------------- Structured Output Model -------------------
class MathReasoning(BaseModel):
    class Step(BaseModel):
        explanation: str
        output: str
    steps: list[Step]
    final_answer: str

# ------------------- Helper: Get Env Var -------------------
def get_env_variable(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Environment variable {name} is not set")
    return value

# ------------------- Azure OpenAI Client Setup -------------------
client = AzureOpenAIChatCompletionClient(
    azure_deployment=get_env_variable("AZURE_OPENAI_DEPLOYMENT_NAME"),
    model=get_env_variable("AZURE_OPENAI_MODEL"),
    api_version=get_env_variable("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=get_env_variable("AZURE_OPENAI_ENDPOINT"),
    api_key=get_env_variable("AZURE_OPENAI_API_KEY"),
)

# ------------------- LLM Usage Tracker -------------------
class LLMUsageTracker(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self._prompt_tokens = 0
        self._completion_tokens = 0
    @property
    def tokens(self) -> int:
        return self._prompt_tokens + self._completion_tokens
    @property
    def prompt_tokens(self) -> int:
        return self._prompt_tokens
    @property
    def completion_tokens(self) -> int:
        return self._completion_tokens
    def reset(self) -> None:
        self._prompt_tokens = 0
        self._completion_tokens = 0
    def emit(self, record: logging.LogRecord) -> None:
        try:
            if isinstance(record.msg, LLMCallEvent):
                event = record.msg
                self._prompt_tokens += event.prompt_tokens
                self._completion_tokens += event.completion_tokens
        except Exception:
            self.handleError(record)

# Attach the usage tracker to the event logger
logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.INFO)
llm_usage = LLMUsageTracker()
logger.handlers = [llm_usage]

# ------------------- Structured Output Call -------------------
async def main():
    messages = [UserMessage(content="What is 16 + 32?", source="user")]
    response = await client.create(messages=messages, extra_create_args={"response_format": MathReasoning})
    response_content: Optional[str] = response.content if isinstance(response.content, str) else None
    if response_content is None:
        raise ValueError("Response content is not a valid JSON string")
    print(json.loads(response_content))
    MathReasoning.model_validate(json.loads(response_content))
    print(f"Prompt tokens: {llm_usage.prompt_tokens}")
    print(f"Completion tokens: {llm_usage.completion_tokens}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
