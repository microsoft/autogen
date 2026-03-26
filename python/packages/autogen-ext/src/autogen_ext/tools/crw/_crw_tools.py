"""CRW web scraping tools for AutoGen agents.

CRW is an open-source web scraper for AI agents. It provides a single Rust binary
with a Firecrawl-compatible REST API. These tools wrap the CRW API endpoints:
- POST /v1/scrape - Scrape a single URL
- POST /v1/crawl - Start a multi-page crawl
- GET /v1/crawl/{id} - Check crawl status and get results
- POST /v1/map - Discover all links on a site

See https://github.com/nicholasgasior/crw for more information.
"""

import asyncio
from typing import Any, Literal, Optional

import httpx
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field


# --- Scrape ---


class ScrapeArgs(BaseModel):
    url: str = Field(..., description="The URL to scrape (http/https only).")
    formats: list[str] = Field(
        default=["markdown"],
        description='Output formats: "markdown", "html", "rawHtml", "plainText", "links".',
    )
    only_main_content: bool = Field(
        default=True,
        description="Strip navigation, footer, and sidebar elements.",
    )
    css_selector: Optional[str] = Field(
        default=None,
        description="Extract only elements matching this CSS selector.",
    )
    render_js: Optional[bool] = Field(
        default=None,
        description="null=auto, true=force JS rendering, false=HTTP only.",
    )
    wait_for: Optional[int] = Field(
        default=None,
        description="Milliseconds to wait after JS rendering.",
    )


class ScrapeResult(BaseModel):
    success: bool
    markdown: Optional[str] = None
    html: Optional[str] = None
    plain_text: Optional[str] = None
    links: Optional[list[str]] = None
    title: Optional[str] = None
    source_url: Optional[str] = None
    error: Optional[str] = None


class CrwScrapeTool(BaseTool[ScrapeArgs, ScrapeResult]):
    """Scrape a single URL and return its content as markdown, HTML, or plain text.

    Uses the CRW web scraper's ``POST /v1/scrape`` endpoint. CRW is an open-source,
    high-performance web scraper built in Rust with a Firecrawl-compatible REST API.

    .. note::
        This tool requires the :code:`crw` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[crw]"

        You must have a CRW server running. Install and start it with:

        .. code-block:: bash

            # Install crw (see https://github.com/nicholasgasior/crw)
            crw --port 3000

    Example:
        Basic usage::

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.crw import CrwScrapeTool

            scrape_tool = CrwScrapeTool(base_url="http://localhost:3000")

            async def main():
                model = OpenAIChatCompletionClient(model="gpt-4o")
                agent = AssistantAgent("web_agent", model_client=model, tools=[scrape_tool])
                result = await agent.on_messages(
                    [TextMessage(content="Scrape https://example.com and summarize it.", source="user")],
                    CancellationToken(),
                )
                print(result.chat_message)

            asyncio.run(main())
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        super().__init__(
            ScrapeArgs,
            ScrapeResult,
            "scrape_url",
            "Scrape a URL and return its content as markdown. Powered by CRW web scraper.",
        )

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def run(self, args: ScrapeArgs, cancellation_token: CancellationToken) -> ScrapeResult:
        payload: dict[str, Any] = {
            "url": args.url,
            "formats": args.formats,
            "onlyMainContent": args.only_main_content,
        }
        if args.css_selector is not None:
            payload["cssSelector"] = args.css_selector
        if args.render_js is not None:
            payload["renderJs"] = args.render_js
        if args.wait_for is not None:
            payload["waitFor"] = args.wait_for

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/scrape",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()

            data = body.get("data", {})
            metadata = data.get("metadata", {})
            return ScrapeResult(
                success=body.get("success", True),
                markdown=data.get("markdown"),
                html=data.get("html"),
                plain_text=data.get("plainText"),
                links=data.get("links"),
                title=metadata.get("title"),
                source_url=metadata.get("sourceURL"),
            )
        except Exception as e:
            return ScrapeResult(success=False, error=str(e))


# --- Crawl ---


class CrawlArgs(BaseModel):
    url: str = Field(..., description="The starting URL for the crawl.")
    max_depth: int = Field(default=2, description="Maximum link-follow depth.")
    max_pages: int = Field(default=100, description="Maximum number of pages to scrape.")
    formats: list[str] = Field(default=["markdown"], description="Output formats for each page.")
    poll: bool = Field(
        default=True,
        description="If true, poll until the crawl completes and return results. If false, return the job ID immediately.",
    )
    poll_interval: float = Field(default=2.0, description="Seconds between status polls when poll=True.")


class CrawlPageResult(BaseModel):
    markdown: Optional[str] = None
    title: Optional[str] = None
    source_url: Optional[str] = None
    status_code: Optional[int] = None


class CrawlResult(BaseModel):
    success: bool
    job_id: Optional[str] = None
    status: Optional[str] = None
    total: Optional[int] = None
    completed: Optional[int] = None
    pages: list[CrawlPageResult] = Field(default_factory=list)
    error: Optional[str] = None


class CrawlStatusResult(BaseModel):
    success: bool
    status: Optional[str] = None
    total: Optional[int] = None
    completed: Optional[int] = None
    pages: list[CrawlPageResult] = Field(default_factory=list)
    error: Optional[str] = None


class CrwCrawlTool(BaseTool[CrawlArgs, CrawlResult]):
    """Crawl a website starting from a URL, following links up to a configurable depth.

    Uses the CRW web scraper's ``POST /v1/crawl`` and ``GET /v1/crawl/{id}`` endpoints.
    By default, this tool polls until the crawl completes and returns all scraped pages.

    .. note::
        This tool requires the :code:`crw` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[crw]"

    Example:
        Basic usage::

            import asyncio

            from autogen_ext.tools.crw import CrwCrawlTool
            from autogen_core import CancellationToken

            crawl_tool = CrwCrawlTool(base_url="http://localhost:3000")

            async def main():
                result = await crawl_tool.run_json(
                    {"url": "https://example.com", "max_depth": 1, "max_pages": 5},
                    CancellationToken(),
                )
                print(result)

            asyncio.run(main())
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
        timeout: float = 300.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        super().__init__(
            CrawlArgs,
            CrawlResult,
            "crawl_website",
            "Crawl a website starting from a URL, following links to discover and scrape multiple pages.",
        )

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def run(self, args: CrawlArgs, cancellation_token: CancellationToken) -> CrawlResult:
        payload: dict[str, Any] = {
            "url": args.url,
            "maxDepth": args.max_depth,
            "maxPages": args.max_pages,
            "formats": args.formats,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/crawl",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()

            job_id = body.get("id")
            if not args.poll:
                return CrawlResult(success=True, job_id=job_id, status="scraping")

            # Poll until completion
            while True:
                await asyncio.sleep(args.poll_interval)
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    status_resp = await client.get(
                        f"{self._base_url}/v1/crawl/{job_id}",
                        headers=self._headers(),
                    )
                    status_resp.raise_for_status()
                    status_body = status_resp.json()

                status = status_body.get("status", "")
                if status in ("completed", "failed"):
                    pages = [
                        CrawlPageResult(
                            markdown=p.get("markdown"),
                            title=p.get("metadata", {}).get("title"),
                            source_url=p.get("metadata", {}).get("sourceURL"),
                            status_code=p.get("metadata", {}).get("statusCode"),
                        )
                        for p in status_body.get("data", [])
                    ]
                    return CrawlResult(
                        success=status == "completed",
                        job_id=job_id,
                        status=status,
                        total=status_body.get("total"),
                        completed=status_body.get("completed"),
                        pages=pages,
                        error=status_body.get("error") if status == "failed" else None,
                    )
        except Exception as e:
            return CrawlResult(success=False, error=str(e))


# --- Map ---


class MapArgs(BaseModel):
    url: str = Field(..., description="The URL to discover links from.")
    max_depth: int = Field(default=2, description="Maximum discovery depth.")
    use_sitemap: bool = Field(default=True, description="Also read sitemap.xml for link discovery.")


class MapResult(BaseModel):
    success: bool
    links: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class CrwMapTool(BaseTool[MapArgs, MapResult]):
    """Discover all links on a website by crawling and reading its sitemap.

    Uses the CRW web scraper's ``POST /v1/map`` endpoint to return a flat list
    of all discovered URLs on a site.

    .. note::
        This tool requires the :code:`crw` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[crw]"

    Example:
        Basic usage::

            import asyncio

            from autogen_ext.tools.crw import CrwMapTool
            from autogen_core import CancellationToken

            map_tool = CrwMapTool(base_url="http://localhost:3000")

            async def main():
                result = await map_tool.run_json(
                    {"url": "https://example.com"},
                    CancellationToken(),
                )
                print(result)

            asyncio.run(main())
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        super().__init__(
            MapArgs,
            MapResult,
            "map_site",
            "Discover all links on a website. Returns a list of URLs found by crawling and reading sitemaps.",
        )

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def run(self, args: MapArgs, cancellation_token: CancellationToken) -> MapResult:
        payload: dict[str, Any] = {
            "url": args.url,
            "maxDepth": args.max_depth,
            "useSitemap": args.use_sitemap,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/map",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()

            return MapResult(
                success=body.get("success", True),
                links=body.get("data", {}).get("links", []),
            )
        except Exception as e:
            return MapResult(success=False, error=str(e))
