import os
from typing import Dict, List, Optional
from urllib.parse import urljoin

import html2text
import httpx
from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool
from bs4 import BeautifulSoup


async def google_search(
    query: str,
    num_results: int = 5,
    include_snippets: bool = True,
    include_content: bool = True,
    content_max_length: Optional[int] = 15000,
    language: str = "en",
    country: Optional[str] = None,
    safe_search: bool = True,
) -> List[Dict[str, str]]:
    """
    Perform a Google search using the Custom Search API and optionally fetch webpage content.

    Args:
        query: Search query string
        num_results: Number of results to return (max 10)
        include_snippets: Include result snippets in output
        include_content: Include full webpage content in markdown format
        content_max_length: Maximum length of webpage content (if included)
        language: Language code for search results (e.g., en, es, fr)
        country: Optional country code for search results (e.g., us, uk)
        safe_search: Enable safe search filtering

    Returns:
        List[Dict[str, str]]: List of search results, each containing:
            - title: Result title
            - link: Result URL
            - snippet: Result description (if include_snippets=True)
            - content: Webpage content in markdown (if include_content=True)
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        raise ValueError("Missing required environment variables. Please set GOOGLE_API_KEY and GOOGLE_CSE_ID.")

    num_results = min(max(1, num_results), 10)

    async def fetch_page_content(url: str, max_length: Optional[int] = 50000) -> str:
        """Helper function to fetch and convert webpage content to markdown"""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Convert relative URLs to absolute
                for tag in soup.find_all(["a", "img"]):
                    if tag.get("href"):
                        tag["href"] = urljoin(url, tag["href"])
                    if tag.get("src"):
                        tag["src"] = urljoin(url, tag["src"])

                h2t = html2text.HTML2Text()
                h2t.body_width = 0
                h2t.ignore_images = False
                h2t.ignore_emphasis = False
                h2t.ignore_links = False
                h2t.ignore_tables = False

                markdown = h2t.handle(str(soup))

                if max_length and len(markdown) > max_length:
                    markdown = markdown[:max_length] + "\n...(truncated)"

                return markdown.strip()

        except Exception as e:
            return f"Error fetching content: {str(e)}"

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": num_results,
        "hl": language,
        "safe": "active" if safe_search else "off",
    }

    if country:
        params["gl"] = country

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            if "items" in data:
                for item in data["items"]:
                    result = {"title": item.get("title", ""), "link": item.get("link", "")}
                    if include_snippets:
                        result["snippet"] = item.get("snippet", "")

                    if include_content:
                        result["content"] = await fetch_page_content(result["link"], max_length=content_max_length)

                    results.append(result)

            return results

    except httpx.RequestError as e:
        raise ValueError(f"Failed to perform search: {str(e)}") from e
    except KeyError as e:
        raise ValueError(f"Invalid API response format: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Error during search: {str(e)}") from e


# Create the enhanced Google search tool
google_search_tool = FunctionTool(
    func=google_search,
    description="""
    Perform Google searches using the Custom Search API with optional webpage content fetching.
    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables to be set.
    """,
    global_imports=[
        ImportFromModule("typing", ("List", "Dict", "Optional")),
        "os",
        "httpx",
        "html2text",
        ImportFromModule("bs4", ("BeautifulSoup",)),
        ImportFromModule("urllib.parse", ("urljoin",)),
    ],
)
