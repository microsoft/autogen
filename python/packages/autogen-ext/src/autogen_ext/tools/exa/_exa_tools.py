"""Exa search tools for AutoGen.

This module provides four tools that wrap the `Exa <https://exa.ai>`_ neural
search API:

* :class:`ExaSearchTool` -- web search with optional text content
* :class:`ExaFindSimilarTool` -- discover pages similar to a given URL
* :class:`ExaGetContentsTool` -- retrieve full text for known URLs
* :class:`ExaAnswerTool` -- AI-generated answer with citations
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional, Sequence, Type, Union

from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing_extensions import Self

logger = logging.getLogger(__name__)

try:
    from exa_py import Exa

    _has_exa = True
except ImportError:
    _has_exa = False

# ---------------------------------------------------------------------------
# Type aliases for the Exa API
# ---------------------------------------------------------------------------

SearchType = Literal[
    "auto",
    "neural",
    "fast",
    "deep-lite",
    "deep",
    "deep-reasoning",
    "instant",
]
Category = Literal[
    "company",
    "research paper",
    "news",
    "pdf",
    "personal site",
    "financial report",
    "people",
]
Livecrawl = Literal["never", "fallback", "always", "preferred"]


# ---------------------------------------------------------------------------
# Config models (for Component serialisation)
# ---------------------------------------------------------------------------


class ExaToolConfig(BaseModel):
    """Shared configuration for all Exa tools."""

    api_key: Optional[str] = None
    """Exa API key.  Falls back to the ``EXA_API_KEY`` env var when *None*."""


class ExaSearchToolConfig(ExaToolConfig):
    """Serialisable configuration for :class:`ExaSearchTool`."""

    num_results: Optional[int] = None
    max_characters: Optional[int] = None
    search_type: Optional[SearchType] = None
    category: Optional[Category] = None
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    start_published_date: Optional[str] = None
    end_published_date: Optional[str] = None
    livecrawl: Optional[Livecrawl] = None
    user_location: Optional[str] = None
    moderation: Optional[bool] = None


class ExaFindSimilarToolConfig(ExaToolConfig):
    """Serialisable configuration for :class:`ExaFindSimilarTool`."""

    num_results: Optional[int] = None
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    exclude_source_domain: Optional[bool] = None
    category: Optional[Category] = None


class ExaGetContentsToolConfig(ExaToolConfig):
    """Serialisable configuration for :class:`ExaGetContentsTool`."""


class ExaAnswerToolConfig(ExaToolConfig):
    """Serialisable configuration for :class:`ExaAnswerTool`."""


# ---------------------------------------------------------------------------
# Pydantic arg / return models
# ---------------------------------------------------------------------------


class ExaSearchArgs(BaseModel):
    """Input parameters for :class:`ExaSearchTool`."""

    query: str = Field(description="The search query string.")


class ExaSearchResultItem(BaseModel):
    """A single search result returned by the Exa API."""

    title: str = Field(description="Page title.")
    url: str = Field(description="Page URL.")
    score: Optional[float] = Field(default=None, description="Relevance score.")
    published_date: Optional[str] = Field(default=None, description="Publication date, if available.")
    author: Optional[str] = Field(default=None, description="Author, if available.")
    text: Optional[str] = Field(default=None, description="Page text content, if requested.")


class ExaSearchResult(BaseModel):
    """Return value of :class:`ExaSearchTool`."""

    query: str = Field(description="The original query.")
    results: List[ExaSearchResultItem] = Field(default_factory=list, description="Ranked search results.")


class ExaFindSimilarArgs(BaseModel):
    """Input parameters for :class:`ExaFindSimilarTool`."""

    url: str = Field(description="The URL to find similar pages for.")


class ExaFindSimilarResult(BaseModel):
    """Return value of :class:`ExaFindSimilarTool`."""

    results: List[ExaSearchResultItem] = Field(default_factory=list, description="Similar pages.")


class ExaGetContentsArgs(BaseModel):
    """Input parameters for :class:`ExaGetContentsTool`."""

    urls: List[str] = Field(description="URLs to fetch content for.")


class ExaContentItem(BaseModel):
    """A content item returned by the Exa get-contents endpoint."""

    url: str = Field(description="Page URL.")
    title: str = Field(description="Page title.")
    text: str = Field(description="Full page text.")
    author: Optional[str] = Field(default=None, description="Author, if available.")
    published_date: Optional[str] = Field(default=None, description="Publication date, if available.")


class ExaGetContentsResult(BaseModel):
    """Return value of :class:`ExaGetContentsTool`."""

    results: List[ExaContentItem] = Field(default_factory=list, description="Content for each URL.")


class ExaAnswerArgs(BaseModel):
    """Input parameters for :class:`ExaAnswerTool`."""

    query: str = Field(description="The question to answer.")


class ExaAnswerCitation(BaseModel):
    """A citation backing an AI-generated answer."""

    url: str = Field(description="Source URL.")
    title: str = Field(description="Source title.")
    text: str = Field(description="Cited passage.")


class ExaAnswerResult(BaseModel):
    """Return value of :class:`ExaAnswerTool`."""

    answer: str = Field(description="The AI-generated answer.")
    citations: List[ExaAnswerCitation] = Field(default_factory=list, description="Supporting citations.")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _clean(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove *None* values so the SDK uses its own defaults."""
    return {k: v for k, v in d.items() if v is not None}


def _make_client(api_key: Optional[str] = None) -> "Exa":
    """Create an :class:`Exa` client with the ``autogen`` integration header."""
    if not _has_exa:
        raise ImportError(
            "The 'exa-py' package is required for Exa tools. " 'Install it with: pip install -U "autogen-ext[exa]"'
        )
    return Exa(api_key=api_key, integration_source="autogen")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class ExaSearchTool(BaseTool[ExaSearchArgs, ExaSearchResult], Component[ExaSearchToolConfig]):
    """Search the web using Exa's neural search engine.

    Returns ranked results with titles, URLs, relevance scores, and optional
    text content.

    .. note::
        This tool requires the :code:`exa` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-ext[exa]"

    Example usage with AssistantAgent:

    .. code-block:: python

        import asyncio

        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.messages import TextMessage
        from autogen_core import CancellationToken
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.tools.exa import ExaSearchTool


        async def main():
            model = OpenAIChatCompletionClient(model="gpt-4o")
            search = ExaSearchTool(num_results=5, search_type="auto")
            agent = AssistantAgent("researcher", model_client=model, tools=[search])
            result = await agent.on_messages(
                [TextMessage(content="Find recent papers on multi-agent systems", source="user")],
                CancellationToken(),
            )
            print(result.chat_message)


        asyncio.run(main())
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.exa.ExaSearchTool"
    component_config_schema = ExaSearchToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        num_results: Optional[int] = None,
        max_characters: Optional[int] = None,
        search_type: Optional[SearchType] = None,
        category: Optional[Category] = None,
        include_domains: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        livecrawl: Optional[Livecrawl] = None,
        user_location: Optional[str] = None,
        moderation: Optional[bool] = None,
        client: Optional[Any] = None,
    ) -> None:
        super().__init__(
            args_type=ExaSearchArgs,
            return_type=ExaSearchResult,
            name="exa_search",
            description=(
                "Search the web using Exa's neural search engine. "
                "Returns ranked results with titles, URLs, relevance scores, and optional text content."
            ),
        )
        self._client = client if client is not None else _make_client(api_key)
        self._api_key = api_key
        self._num_results = num_results
        self._max_characters = max_characters
        self._search_type = search_type
        self._category = category
        self._include_domains = list(include_domains) if include_domains is not None else None
        self._exclude_domains = list(exclude_domains) if exclude_domains is not None else None
        self._start_published_date = start_published_date
        self._end_published_date = end_published_date
        self._livecrawl = livecrawl
        self._user_location = user_location
        self._moderation = moderation

    async def run(self, args: ExaSearchArgs, cancellation_token: CancellationToken) -> ExaSearchResult:
        kwargs = _clean(
            {
                "num_results": self._num_results,
                "type": self._search_type,
                "category": self._category,
                "include_domains": self._include_domains,
                "exclude_domains": self._exclude_domains,
                "start_published_date": self._start_published_date,
                "end_published_date": self._end_published_date,
                "livecrawl": self._livecrawl,
                "user_location": self._user_location,
                "moderation": self._moderation,
            }
        )
        if self._max_characters is not None:
            kwargs["contents"] = {"text": {"max_characters": self._max_characters}}

        raw = self._client.search(args.query, **kwargs)

        return ExaSearchResult(
            query=args.query,
            results=[
                ExaSearchResultItem(
                    title=r.title or "",
                    url=r.url,
                    score=r.score,
                    published_date=r.published_date,
                    author=r.author,
                    text=r.text,
                )
                for r in raw.results
            ],
        )

    def _to_config(self) -> ExaSearchToolConfig:
        return ExaSearchToolConfig(
            api_key=self._api_key,
            num_results=self._num_results,
            max_characters=self._max_characters,
            search_type=self._search_type,
            category=self._category,
            include_domains=self._include_domains,
            exclude_domains=self._exclude_domains,
            start_published_date=self._start_published_date,
            end_published_date=self._end_published_date,
            livecrawl=self._livecrawl,
            user_location=self._user_location,
            moderation=self._moderation,
        )

    @classmethod
    def _from_config(cls, config: ExaSearchToolConfig) -> Self:
        return cls(
            api_key=config.api_key,
            num_results=config.num_results,
            max_characters=config.max_characters,
            search_type=config.search_type,
            category=config.category,
            include_domains=config.include_domains,
            exclude_domains=config.exclude_domains,
            start_published_date=config.start_published_date,
            end_published_date=config.end_published_date,
            livecrawl=config.livecrawl,
            user_location=config.user_location,
            moderation=config.moderation,
        )


class ExaFindSimilarTool(BaseTool[ExaFindSimilarArgs, ExaFindSimilarResult], Component[ExaFindSimilarToolConfig]):
    """Find web pages similar to a given URL.

    Useful for discovering related content, competitors, or alternative sources.

    .. note::
        This tool requires the :code:`exa` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-ext[exa]"

    Example:

    .. code-block:: python

        from autogen_ext.tools.exa import ExaFindSimilarTool

        tool = ExaFindSimilarTool(num_results=5)
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.exa.ExaFindSimilarTool"
    component_config_schema = ExaFindSimilarToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        num_results: Optional[int] = None,
        include_domains: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[Category] = None,
        client: Optional[Any] = None,
    ) -> None:
        super().__init__(
            args_type=ExaFindSimilarArgs,
            return_type=ExaFindSimilarResult,
            name="exa_find_similar",
            description=(
                "Find web pages similar to a given URL. "
                "Useful for discovering related content, competitors, or alternative sources."
            ),
        )
        self._client = client if client is not None else _make_client(api_key)
        self._api_key = api_key
        self._num_results = num_results
        self._include_domains = list(include_domains) if include_domains is not None else None
        self._exclude_domains = list(exclude_domains) if exclude_domains is not None else None
        self._exclude_source_domain = exclude_source_domain
        self._category = category

    async def run(self, args: ExaFindSimilarArgs, cancellation_token: CancellationToken) -> ExaFindSimilarResult:
        kwargs = _clean(
            {
                "num_results": self._num_results,
                "include_domains": self._include_domains,
                "exclude_domains": self._exclude_domains,
                "exclude_source_domain": self._exclude_source_domain,
                "category": self._category,
            }
        )
        raw = self._client.find_similar(args.url, **kwargs)
        return ExaFindSimilarResult(
            results=[
                ExaSearchResultItem(
                    title=r.title or "",
                    url=r.url,
                    score=r.score,
                    published_date=r.published_date,
                    author=r.author,
                    text=r.text,
                )
                for r in raw.results
            ],
        )

    def _to_config(self) -> ExaFindSimilarToolConfig:
        return ExaFindSimilarToolConfig(
            api_key=self._api_key,
            num_results=self._num_results,
            include_domains=self._include_domains,
            exclude_domains=self._exclude_domains,
            exclude_source_domain=self._exclude_source_domain,
            category=self._category,
        )

    @classmethod
    def _from_config(cls, config: ExaFindSimilarToolConfig) -> Self:
        return cls(
            api_key=config.api_key,
            num_results=config.num_results,
            include_domains=config.include_domains,
            exclude_domains=config.exclude_domains,
            exclude_source_domain=config.exclude_source_domain,
            category=config.category,
        )


class ExaGetContentsTool(BaseTool[ExaGetContentsArgs, ExaGetContentsResult], Component[ExaGetContentsToolConfig]):
    """Retrieve the full text content of specific URLs via the Exa API.

    Useful when you already know which pages you need and want to read their
    full contents.

    .. note::
        This tool requires the :code:`exa` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-ext[exa]"

    Example:

    .. code-block:: python

        from autogen_ext.tools.exa import ExaGetContentsTool

        tool = ExaGetContentsTool()
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.exa.ExaGetContentsTool"
    component_config_schema = ExaGetContentsToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        client: Optional[Any] = None,
    ) -> None:
        super().__init__(
            args_type=ExaGetContentsArgs,
            return_type=ExaGetContentsResult,
            name="exa_get_contents",
            description=(
                "Get the full text content of specific URLs. "
                "Useful when you already know which pages you need and want to read them."
            ),
        )
        self._client = client if client is not None else _make_client(api_key)
        self._api_key = api_key

    async def run(self, args: ExaGetContentsArgs, cancellation_token: CancellationToken) -> ExaGetContentsResult:
        raw = self._client.get_contents(args.urls, text=True)
        return ExaGetContentsResult(
            results=[
                ExaContentItem(
                    url=r.url,
                    title=r.title or "",
                    text=r.text or "",
                    author=r.author,
                    published_date=r.published_date,
                )
                for r in raw.results
            ],
        )

    def _to_config(self) -> ExaGetContentsToolConfig:
        return ExaGetContentsToolConfig(api_key=self._api_key)

    @classmethod
    def _from_config(cls, config: ExaGetContentsToolConfig) -> Self:
        return cls(api_key=config.api_key)


class ExaAnswerTool(BaseTool[ExaAnswerArgs, ExaAnswerResult], Component[ExaAnswerToolConfig]):
    """Generate an AI-powered answer to a question with citations from web sources.

    This wraps the Exa ``/answer`` endpoint which performs a search and then
    synthesises a concise answer grounded in the retrieved documents.

    .. note::
        This tool requires the :code:`exa` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-ext[exa]"

    Example:

    .. code-block:: python

        from autogen_ext.tools.exa import ExaAnswerTool

        tool = ExaAnswerTool()
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.exa.ExaAnswerTool"
    component_config_schema = ExaAnswerToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        client: Optional[Any] = None,
    ) -> None:
        super().__init__(
            args_type=ExaAnswerArgs,
            return_type=ExaAnswerResult,
            name="exa_answer",
            description="Generate an AI-powered answer to a question with citations from web sources.",
        )
        self._client = client if client is not None else _make_client(api_key)
        self._api_key = api_key

    async def run(self, args: ExaAnswerArgs, cancellation_token: CancellationToken) -> ExaAnswerResult:
        raw = self._client.answer(args.query, text=True)
        return ExaAnswerResult(
            answer=raw.answer,
            citations=[
                ExaAnswerCitation(
                    url=c.url,
                    title=c.title or "",
                    text=c.text or "",
                )
                for c in (raw.citations or [])
            ],
        )

    def _to_config(self) -> ExaAnswerToolConfig:
        return ExaAnswerToolConfig(api_key=self._api_key)

    @classmethod
    def _from_config(cls, config: ExaAnswerToolConfig) -> Self:
        return cls(api_key=config.api_key)
