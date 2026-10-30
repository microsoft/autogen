"""
ModelsLab model client for AutoGen.

Provides a pre-configured `ChatCompletionClient` for ModelsLab's uncensored
Llama 3.1 models via an OpenAI-compatible endpoint.

Get your API key at: https://modelslab.com
API docs: https://docs.modelslab.com/uncensored-chat
"""

import os
from typing import Any, Dict, Optional

from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient

MODELSLAB_API_BASE = "https://modelslab.com/uncensored-chat/v1"

# ModelInfo for each supported ModelsLab model.
# Llama 3.1 uncensored models: no vision, basic function calling, 128K context.
_MODELSLAB_MODEL_INFO: Dict[str, ModelInfo] = {
    "llama-3.1-8b-uncensored": ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=False,
        context_length=131072,
    ),
    "llama-3.1-70b-uncensored": ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=False,
        context_length=131072,
    ),
}

_DEFAULT_MODEL_INFO = ModelInfo(
    vision=False,
    function_calling=True,
    json_output=True,
    family=ModelFamily.UNKNOWN,
    structured_output=False,
    context_length=131072,
)


class ModelsLabChatCompletionClient(OpenAIChatCompletionClient):
    """
    Chat completion client for ModelsLab's uncensored Llama 3.1 models.

    ModelsLab provides Llama 3.1 8B and 70B models with no content restrictions
    and 128K token context windows, accessible via an OpenAI-compatible API.

    This client pre-configures the API base URL and model information so you
    don't need to set them manually.

    .. code-block:: python

        import asyncio
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.ui import Console
        from autogen_agentchat.conditions import TextMentionTermination
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_ext.models.modelslab import ModelsLabChatCompletionClient

        model_client = ModelsLabChatCompletionClient(
            model="llama-3.1-8b-uncensored",
            # api_key="your-key" or set MODELSLAB_API_KEY env var
        )

        async def main():
            agent = AssistantAgent(
                name="assistant",
                model_client=model_client,
                system_message="You are a helpful AI assistant.",
            )
            await Console(agent.run_stream(task="Write a Python quicksort."))

        asyncio.run(main())

    **Models:**

    +----------------------------------+----------+-------------------------------+
    | Model                            | Context  | Notes                         |
    +==================================+==========+===============================+
    | ``llama-3.1-8b-uncensored``      | 128K     | Fast, efficient (default)     |
    +----------------------------------+----------+-------------------------------+
    | ``llama-3.1-70b-uncensored``     | 128K     | Higher quality                |
    +----------------------------------+----------+-------------------------------+

    Get your API key at: https://modelslab.com
    """

    def __init__(
        self,
        model: str = "llama-3.1-8b-uncensored",
        api_key: Optional[str] = None,
        model_info: Optional[ModelInfo] = None,
        **kwargs: Any,
    ) -> None:
        """
        Create a ModelsLabChatCompletionClient.

        :param model: Model ID. Defaults to ``llama-3.1-8b-uncensored``.
        :param api_key: ModelsLab API key. Falls back to ``MODELSLAB_API_KEY``
            environment variable if not provided.
        :param model_info: Optional :class:`ModelInfo` override for capabilities
            and context length. Uses built-in defaults for known models.
        :param kwargs: Additional keyword arguments forwarded to
            :class:`OpenAIChatCompletionClient`.
        """
        resolved_api_key = api_key or os.environ.get("MODELSLAB_API_KEY")
        if not resolved_api_key:
            raise ValueError(
                "ModelsLab API key not found. "
                "Set MODELSLAB_API_KEY environment variable or pass api_key directly. "
                "Get your key at https://modelslab.com"
            )

        resolved_model_info = (
            model_info
            or _MODELSLAB_MODEL_INFO.get(model)
            or _DEFAULT_MODEL_INFO
        )

        super().__init__(
            model=model,
            api_key=resolved_api_key,
            base_url=MODELSLAB_API_BASE,
            model_info=resolved_model_info,
            **kwargs,
        )
