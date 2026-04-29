"""Perplexity Search API tool for AutoGen.

Calls ``POST https://api.perplexity.ai/search`` and returns ranked web results.
See https://docs.perplexity.ai/docs/search/quickstart and
https://docs.perplexity.ai/api-reference/search-post for the API contract.
"""

from __future__ import annotations

import os
from typing import Any, List, Literal, Optional

import httpx
from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field, SecretStr
from typing_extensions import Self

DEFAULT_BASE_URL = "https://api.perplexity.ai"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RESULTS = 5

RecencyFilter = Literal["hour", "day", "week", "month", "year"]


class PerplexitySearchResult(BaseModel):
    """A single ranked result returned by the Perplexity Search API."""

    title: str
    url: str
    snippet: str = ""
    date: Optional[str] = None


class PerplexitySearchResponse(BaseModel):
    """Response returned by :class:`PerplexitySearchTool`."""

    results: List[PerplexitySearchResult]


class PerplexitySearchToolArgs(BaseModel):
    """Arguments accepted by :class:`PerplexitySearchTool`."""

    query: str = Field(..., description="The natural-language search query.")
    max_results: int = Field(
        default=DEFAULT_MAX_RESULTS,
        ge=1,
        le=20,
        description="Maximum number of results to return.",
    )
    search_domain_filter: Optional[List[str]] = Field(
        default=None,
        description=(
            "Restrict results to (or away from) specific domains. Prefix a "
            "domain with '-' to exclude it (e.g. '-pinterest.com'). Allow- "
            "and deny-lists must NOT be mixed in a single call."
        ),
    )
    search_recency_filter: Optional[RecencyFilter] = Field(
        default=None,
        description="Restrict results to a recent time window: hour, day, week, month, or year.",
    )


class PerplexitySearchToolConfig(BaseModel):
    """Config schema used by :class:`PerplexitySearchTool` for component (de)serialization."""

    api_key: Optional[SecretStr] = None
    base_url: str = DEFAULT_BASE_URL
    default_max_results: int = DEFAULT_MAX_RESULTS
    timeout: float = DEFAULT_TIMEOUT


class PerplexitySearchTool(
    BaseTool[PerplexitySearchToolArgs, PerplexitySearchResponse],
    Component[PerplexitySearchToolConfig],
):
    """Search the web using the Perplexity Search API.

    Returns a list of ranked web results (title, URL, snippet, optional date).
    Useful for grounding agents on up-to-date information.

    The API key is taken from ``api_key`` if provided, otherwise
    ``PERPLEXITY_API_KEY`` (or ``PPLX_API_KEY``) from the environment.

    Install with::

        pip install -U "autogen-ext[perplexity]"

    Args:
        api_key: Perplexity API key. Falls back to ``PERPLEXITY_API_KEY`` /
            ``PPLX_API_KEY`` env var if not provided.
        base_url: Override the API base URL (defaults to ``https://api.perplexity.ai``).
        default_max_results: Default cap on number of results when ``max_results``
            is not supplied in a call.
        timeout: HTTP timeout in seconds.

    Example:
        .. code-block:: python

            import asyncio
            from autogen_core import CancellationToken
            from autogen_ext.tools.perplexity import PerplexitySearchTool, PerplexitySearchToolArgs


            async def main() -> None:
                tool = PerplexitySearchTool()
                results = await tool.run(
                    PerplexitySearchToolArgs(query="latest LLM benchmarks", max_results=3),
                    CancellationToken(),
                )
                for r in results:
                    print(r.title, r.url)


            asyncio.run(main())
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.perplexity.PerplexitySearchTool"
    component_config_schema = PerplexitySearchToolConfig

    name = "perplexity_search"
    description = "Search the web for up-to-date information using the Perplexity Search API."

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        default_max_results: int = DEFAULT_MAX_RESULTS,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(
            args_type=PerplexitySearchToolArgs,
            return_type=PerplexitySearchResponse,
            name=self.name,
            description=self.description,
        )
        self._api_key = api_key or os.environ.get("PERPLEXITY_API_KEY") or os.environ.get("PPLX_API_KEY")
        self._base_url = base_url.rstrip("/")
        self._default_max_results = default_max_results
        self._timeout = timeout

    def _to_config(self) -> PerplexitySearchToolConfig:
        return PerplexitySearchToolConfig(
            api_key=SecretStr(self._api_key) if self._api_key else None,
            base_url=self._base_url,
            default_max_results=self._default_max_results,
            timeout=self._timeout,
        )

    @classmethod
    def _from_config(cls, config: PerplexitySearchToolConfig) -> Self:
        api_key = config.api_key.get_secret_value() if config.api_key is not None else None
        return cls(
            api_key=api_key,
            base_url=config.base_url,
            default_max_results=config.default_max_results,
            timeout=config.timeout,
        )

    async def run(
        self,
        args: PerplexitySearchToolArgs,
        cancellation_token: CancellationToken,
    ) -> PerplexitySearchResponse:
        if not self._api_key:
            raise ValueError(
                "Perplexity API key not provided. Pass api_key=... or set the "
                "PERPLEXITY_API_KEY (or PPLX_API_KEY) environment variable."
            )

        payload: dict[str, Any] = {
            "query": args.query,
            "max_results": args.max_results or self._default_max_results,
        }
        if args.search_domain_filter:
            payload["search_domain_filter"] = args.search_domain_filter
        if args.search_recency_filter:
            payload["search_recency_filter"] = args.search_recency_filter

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
            response = await client.post(
                f"{self._base_url}/search",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        items = data.get("results", []) or []
        return PerplexitySearchResponse(
            results=[
                PerplexitySearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    date=item.get("date"),
                )
                for item in items
            ]
        )
