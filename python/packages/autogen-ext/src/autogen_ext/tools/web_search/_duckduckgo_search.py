# DuckDuckGo Search Tool created by Varad Srivastava
from typing import Dict, List, Optional, Union
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import html2text
import httpx
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from bs4 import BeautifulSoup, NavigableString, Tag
from pydantic import BaseModel, Field


class DuckDuckGoSearchArgs(BaseModel):
    """Arguments for DuckDuckGo search."""

    query: str = Field(..., description="Search query string")
    num_results: int = Field(default=3, description="Number of results to return (max 10)")
    include_snippets: bool = Field(default=True, description="Include result snippets in output")
    include_content: bool = Field(default=True, description="Include full webpage content in markdown format")
    content_max_length: Optional[int] = Field(
        default=10000, description="Maximum length of webpage content (if included)"
    )
    language: str = Field(default="en", description="Language code for search results (e.g., en, es, fr)")
    region: Optional[str] = Field(default=None, description="Optional region code for search results (e.g., us, uk)")
    safe_search: bool = Field(default=True, description="Enable safe search filtering")


class DuckDuckGoSearchResult(BaseModel):
    """Result from DuckDuckGo search."""

    results: List[Dict[str, str]] = Field(description="List of search results")


class DuckDuckGoSearchTool(BaseTool[DuckDuckGoSearchArgs, DuckDuckGoSearchResult]):
    """
    A tool for performing DuckDuckGo web searches.

    This tool uses DuckDuckGo's HTML interface to perform web searches without requiring
    an API key. It can optionally fetch and convert webpage content to markdown format.

    Example:
        ```python
        from autogen_ext.tools.web_search import DuckDuckGoSearchTool
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        # Create the search tool
        search_tool = DuckDuckGoSearchTool()

        # Create an agent with the search tool
        model_client = OpenAIChatCompletionClient(model="gpt-4")
        agent = AssistantAgent(name="search_agent", model_client=model_client, tools=[search_tool])
        ```
    """

    def __init__(self) -> None:
        super().__init__(
            args_type=DuckDuckGoSearchArgs,
            return_type=DuckDuckGoSearchResult,
            name="duckduckgo_search",
            description="Perform DuckDuckGo searches with optional webpage content fetching. No API key required.",
        )

    async def run(self, args: DuckDuckGoSearchArgs, cancellation_token: CancellationToken) -> DuckDuckGoSearchResult:
        """Execute the DuckDuckGo search."""
        num_results = min(max(1, args.num_results), 10)

        async def fetch_page_content(url: str, max_length: Optional[int] = 50000) -> str:
            """Helper function to fetch and convert webpage content to markdown"""
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=10)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, "html.parser")

                    # Remove unwanted elements that typically contain navigation/boilerplate
                    for element in soup(
                        ["script", "style", "nav", "header", "footer", "aside", "menu", "form", "button", "input"]
                    ):
                        if hasattr(element, "decompose"):  # type: ignore
                            element.decompose()  # type: ignore

                    # Try to find main content areas first (in order of preference)
                    main_content: Optional[Union[Tag, NavigableString]] = None  # type: ignore
                    content_selectors = [
                        "main",
                        "article",
                        "[role='main']",
                        ".content",
                        ".post",
                        ".entry",
                        ".article-content",
                        ".post-content",
                        ".main-content",
                        ".page-content",
                        "#content",
                        "#main",
                        "#article",
                        ".container .content",
                    ]

                    for selector in content_selectors:
                        main_content = soup.select_one(selector)  # type: ignore
                        if main_content and main_content.get_text(strip=True):
                            break

                    # If no main content found, try to get the largest text block
                    if not main_content or not main_content.get_text(strip=True):
                        # Find all divs and get the one with most text content
                        all_divs = soup.find_all("div")
                        if all_divs:
                            main_content = max(all_divs, key=lambda div: len(div.get_text(strip=True)))

                    # Final fallback: use body but clean it up
                    if not main_content or len(main_content.get_text(strip=True)) < 100:
                        main_content = soup.find("body") or soup

                        # Only remove clearly problematic elements for fallback
                        if hasattr(main_content, "find_all"):  # type: ignore
                            for element in main_content.find_all(["iframe", "embed", "object", "video", "audio"]):  # type: ignore
                                if hasattr(element, "decompose"):  # type: ignore
                                    element.decompose()  # type: ignore

                            # Remove elements with obvious navigation class names (less aggressive)
                            for class_name in ["navigation", "navbar", "sidebar", "footer", "header"]:
                                # Find elements with navigation class names using a simpler approach
                                nav_elements = []  # type: ignore
                                try:
                                    nav_elements = main_content.find_all(class_=class_name)  # type: ignore
                                except Exception:  # type: ignore
                                    # If direct class search fails, try finding elements that contain the class name
                                    try:
                                        all_elements = main_content.find_all()  # type: ignore
                                        for elem in all_elements:  # type: ignore
                                            if hasattr(elem, "get") and elem.get("class"):  # type: ignore
                                                elem_classes = elem.get("class")  # type: ignore
                                                if isinstance(elem_classes, list) and any(
                                                    class_name in str(cls).lower()  # type: ignore
                                                    for cls in elem_classes  # type: ignore
                                                ):  # type: ignore
                                                    nav_elements.append(elem)  # type: ignore
                                    except Exception:  # type: ignore
                                        pass  # type: ignore

                                for element in nav_elements:  # type: ignore
                                    if hasattr(element, "decompose"):  # type: ignore
                                        element.decompose()  # type: ignore

                    # Convert relative URLs to absolute
                    if hasattr(main_content, "find_all"):  # type: ignore
                        for tag in main_content.find_all(["a", "img"]):  # type: ignore
                            if hasattr(tag, "get"):  # type: ignore
                                if tag.get("href"):  # type: ignore
                                    tag["href"] = urljoin(url, str(tag.get("href")))  # type: ignore
                                if tag.get("src"):  # type: ignore
                                    tag["src"] = urljoin(url, str(tag.get("src")))  # type: ignore

                    h2t = html2text.HTML2Text()
                    h2t.body_width = 0
                    h2t.ignore_images = True  # Ignore images to reduce noise
                    h2t.ignore_emphasis = False
                    h2t.ignore_links = True  # Ignore links to reduce noise
                    h2t.ignore_tables = False

                    markdown = h2t.handle(str(main_content))

                    # Clean up the markdown - remove excessive whitespace and empty lines
                    lines: List[str] = markdown.split("\n")
                    cleaned_lines: List[str] = []
                    for line in lines:
                        line = line.strip()
                        # Keep lines that have content (not just headers or empty)
                        if line and (not line.startswith("#") or len(line.split()) > 1):
                            cleaned_lines.append(line)

                    # Remove consecutive empty lines but keep some structure
                    final_lines: List[str] = []
                    prev_empty = False
                    for line in cleaned_lines:
                        if line.strip():
                            final_lines.append(line)
                            prev_empty = False
                        elif not prev_empty and len(final_lines) > 0:
                            final_lines.append("")
                            prev_empty = True

                    markdown = "\n".join(final_lines)

                    # If we still don't have much content, return a basic text extraction
                    if len(markdown.strip()) < 50:
                        text_content = (
                            main_content.get_text(separator="\n", strip=True)
                            if hasattr(main_content, "get_text")
                            else ""
                        )
                        if text_content:
                            lines = [line.strip() for line in text_content.split("\n") if line.strip()]
                            markdown = "\n".join(lines[:50])  # Take first 50 non-empty lines
                        else:
                            markdown = "Content could not be extracted from this page."

                    if max_length and len(markdown) > max_length:
                        markdown = markdown[:max_length] + "\n...(truncated)"

                    return markdown.strip()

            except Exception as e:
                return f"Error fetching content: {str(e)}"

        # Build DuckDuckGo search URL
        params = {
            "q": args.query,
            "kl": args.language,
            "kad": args.region.upper() if args.region else None,
            "safesearch": "1" if args.safe_search else "0",
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        search_url = f"https://html.duckduckgo.com/html/?{quote_plus(args.query)}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, params=params, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                results: List[Dict[str, str]] = []

                # Find all result elements
                result_elements = soup.find_all("div", class_="result")

                for element in result_elements[:num_results]:
                    title_element = element.find("a", class_="result__a")
                    snippet_element = element.find("a", class_="result__snippet")

                    if title_element:
                        raw_link = title_element.get("href", "") or ""

                        # Handle DuckDuckGo redirect URLs and protocol-relative URLs
                        if raw_link.startswith("//duckduckgo.com/l/"):
                            # Extract the actual URL from DuckDuckGo redirect
                            parsed = parse_qs(urlparse(raw_link).query)
                            actual_url_list = parsed.get("uddg", [""])
                            if actual_url_list and actual_url_list[0]:
                                link = unquote(actual_url_list[0])
                            else:
                                link = "https:" + raw_link
                        elif raw_link.startswith("//"):
                            # Protocol-relative URL
                            link = "https:" + raw_link
                        elif raw_link.startswith("/"):
                            # Relative URL
                            link = "https://duckduckgo.com" + raw_link
                        else:
                            # Absolute URL
                            link = raw_link

                        result: Dict[str, str] = {"title": title_element.get_text(strip=True), "link": link}

                        if args.include_snippets and snippet_element:
                            result["snippet"] = snippet_element.get_text(strip=True)

                        if args.include_content and link.startswith(("http://", "https://")):
                            result["content"] = await fetch_page_content(link, max_length=args.content_max_length)
                        elif args.include_content:
                            result["content"] = "Error: Invalid URL format"

                        results.append(result)

                return DuckDuckGoSearchResult(results=results)

        except httpx.RequestError as e:
            raise ValueError(f"Failed to perform search: {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Error during search: {str(e)}") from e
