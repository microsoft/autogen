"""Perplexity chat completion client for AutoGen.

Perplexity's chat completions endpoint is OpenAI-compatible, so this client
wraps :class:`~autogen_ext.models.openai.OpenAIChatCompletionClient` with the
Perplexity base URL and a sensible default ``model_info`` block, while reading
``PERPLEXITY_API_KEY`` (or ``PPLX_API_KEY``) from the environment.

See https://docs.perplexity.ai/docs/agent/quickstart for endpoint details.
"""

from __future__ import annotations

import os
from typing import Any

from autogen_core.models import ModelFamily, ModelInfo

from ..openai import OpenAIChatCompletionClient

PERPLEXITY_BASE_URL = "https://api.perplexity.ai"

_DEFAULT_MODEL_INFO: ModelInfo = {
    "vision": False,
    "function_calling": True,
    "json_output": True,
    "family": ModelFamily.UNKNOWN,
    "structured_output": True,
}


class PerplexityChatCompletionClient(OpenAIChatCompletionClient):
    """Chat completion client for Perplexity.

    Wraps :class:`~autogen_ext.models.openai.OpenAIChatCompletionClient` with
    Perplexity's OpenAI-compatible endpoint at ``https://api.perplexity.ai``.

    The API key is taken from the ``api_key`` argument, falling back to the
    ``PERPLEXITY_API_KEY`` env var, then ``PPLX_API_KEY``. ``base_url`` defaults
    to :data:`PERPLEXITY_BASE_URL` and can be overridden if you need to point
    at an alternative gateway.

    To use this client, install the ``perplexity`` extra::

        pip install -U "autogen-ext[perplexity]"

    Args:
        model: The Perplexity model identifier (e.g. one of the chat-completion
            models documented at https://docs.perplexity.ai/docs/agent/models).
        api_key: API key. Defaults to ``PERPLEXITY_API_KEY`` or ``PPLX_API_KEY``.
        base_url: API base URL. Defaults to ``https://api.perplexity.ai``.
        model_info: Optional :class:`ModelInfo`. A reasonable default is supplied.
        **kwargs: Forwarded to :class:`OpenAIChatCompletionClient`.

    Example:
        .. code-block:: python

            import asyncio
            from autogen_core.models import UserMessage
            from autogen_ext.models.perplexity import PerplexityChatCompletionClient


            async def main() -> None:
                client = PerplexityChatCompletionClient(model="sonar")
                result = await client.create([UserMessage(content="What is RAG?", source="user")])
                print(result.content)
                await client.close()


            asyncio.run(main())
    """

    component_provider_override = "autogen_ext.models.perplexity.PerplexityChatCompletionClient"

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model_info: ModelInfo | None = None,
        **kwargs: Any,
    ) -> None:
        resolved_api_key = api_key or os.environ.get("PERPLEXITY_API_KEY") or os.environ.get("PPLX_API_KEY")
        if not resolved_api_key:
            raise ValueError(
                "Perplexity API key not provided. Pass api_key=... or set the "
                "PERPLEXITY_API_KEY (or PPLX_API_KEY) environment variable."
            )

        super().__init__(
            model=model,
            api_key=resolved_api_key,
            base_url=base_url or PERPLEXITY_BASE_URL,
            model_info=model_info or _DEFAULT_MODEL_INFO,
            **kwargs,
        )
