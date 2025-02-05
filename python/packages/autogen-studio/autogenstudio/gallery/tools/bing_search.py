import json
import os
from typing import Dict, List, Optional
from urllib.parse import urljoin

import html2text
import httpx
from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool
from bs4 import BeautifulSoup


async def bing_search(
    query: str,
    num_results: int = 5,
    include_snippets: bool = True,
    include_content: bool = True,
    content_max_length: Optional[int] = 15000,
    language: str = "en",
    country: Optional[str] = None,
    safe_search: str = "moderate",
    response_filter: str = "webpages",
) -> List[Dict[str, str]]:
    """
    Perform a Bing search using the Bing Web Search API.

    Args:
        query: Search query string
        num_results: Number of results to return (max 50)
        include_snippets: Include result snippets in output
        include_content: Include full webpage content in markdown format
        content_max_length: Maximum length of webpage content (if included)
        language: Language code for search results (e.g., 'en', 'es', 'fr')
        country: Optional market code for search results (e.g., 'us', 'uk')
        safe_search: SafeSearch setting ('off', 'moderate', or 'strict')
        response_filter: Type of results ('webpages', 'news', 'images', or 'videos')

    Returns:
        List[Dict[str, str]]: List of search results

    Raises:
        ValueError: If API credentials are invalid or request fails
    """
    # Get and validate API key
    api_key = os.getenv("BING_SEARCH_KEY", "").strip()

    if not api_key:
        raise ValueError(
            "BING_SEARCH_KEY environment variable is not set. " "Please obtain an API key from Azure Portal."
        )

    # Validate safe_search parameter
    valid_safe_search = ["off", "moderate", "strict"]
    if safe_search.lower() not in valid_safe_search:
        raise ValueError(f"Invalid safe_search value. Must be one of: {', '.join(valid_safe_search)}")

    # Validate response_filter parameter
    valid_filters = ["webpages", "news", "images", "videos"]
    if response_filter.lower() not in valid_filters:
        raise ValueError(f"Invalid response_filter value. Must be one of: {', '.join(valid_filters)}")

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

    # Build request headers and parameters
    headers = {"Ocp-Apim-Subscription-Key": api_key, "Accept": "application/json"}

    params = {
        "q": query,
        "count": min(max(1, num_results), 50),
        "mkt": f"{language}-{country.upper()}" if country else language,
        "safeSearch": safe_search.capitalize(),
        "responseFilter": response_filter,
        "textFormat": "raw",
    }

    # Make the request
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params, timeout=10
            )

            # Handle common error cases
            if response.status_code == 401:
                raise ValueError("Authentication failed. Please verify your Bing Search API key.")
            elif response.status_code == 403:
                raise ValueError(
                    "Access forbidden. This could mean:\n"
                    "1. The API key is invalid\n"
                    "2. The API key has expired\n"
                    "3. You've exceeded your API quota"
                )
            elif response.status_code == 429:
                raise ValueError("API quota exceeded. Please try again later.")

            response.raise_for_status()
            data = response.json()

        # Process results based on response_filter
        results = []
        if response_filter == "webpages" and "webPages" in data:
            items = data["webPages"]["value"]
        elif response_filter == "news" and "news" in data:
            items = data["news"]["value"]
        elif response_filter == "images" and "images" in data:
            items = data["images"]["value"]
        elif response_filter == "videos" and "videos" in data:
            items = data["videos"]["value"]
        else:
            if not any(key in data for key in ["webPages", "news", "images", "videos"]):
                return []  # No results found
            raise ValueError(f"No {response_filter} results found in API response")

        # Extract relevant information based on result type
        for item in items:
            result = {"title": item.get("name", "")}

            if response_filter == "webpages":
                result["link"] = item.get("url", "")
                if include_snippets:
                    result["snippet"] = item.get("snippet", "")
                if include_content:
                    result["content"] = await fetch_page_content(result["link"], max_length=content_max_length)

            elif response_filter == "news":
                result["link"] = item.get("url", "")
                if include_snippets:
                    result["snippet"] = item.get("description", "")
                result["date"] = item.get("datePublished", "")
                if include_content:
                    result["content"] = await fetch_page_content(result["link"], max_length=content_max_length)

            elif response_filter == "images":
                result["link"] = item.get("contentUrl", "")
                result["thumbnail"] = item.get("thumbnailUrl", "")
                if include_snippets:
                    result["snippet"] = item.get("description", "")

            elif response_filter == "videos":
                result["link"] = item.get("contentUrl", "")
                result["thumbnail"] = item.get("thumbnailUrl", "")
                if include_snippets:
                    result["snippet"] = item.get("description", "")
                result["duration"] = item.get("duration", "")

            results.append(result)

        return results[:num_results]

    except httpx.RequestException as e:
        error_msg = str(e)
        if "InvalidApiKey" in error_msg:
            raise ValueError("Invalid API key. Please check your BING_SEARCH_KEY environment variable.") from e
        elif "KeyExpired" in error_msg:
            raise ValueError("API key has expired. Please generate a new key.") from e
        else:
            raise ValueError(f"Search request failed: {error_msg}") from e
    except json.JSONDecodeError:
        raise ValueError("Failed to parse API response. " "Please verify your API credentials and try again.") from None
    except Exception as e:
        raise ValueError(f"Unexpected error during search: {str(e)}") from e


# Create the Bing search tool
bing_search_tool = FunctionTool(
    func=bing_search,
    description="""
    Perform Bing searches using the Bing Web Search API. Requires BING_SEARCH_KEY environment variable.
    Supports web, news, image, and video searches.
    See function documentation for detailed setup instructions.
    """,
    global_imports=[
        ImportFromModule("typing", ("List", "Dict", "Optional")),
        "os",
        "httpx",
        "json",
        "html2text",
        ImportFromModule("bs4", ("BeautifulSoup",)),
        ImportFromModule("urllib.parse", ("urljoin",)),
    ],
)
