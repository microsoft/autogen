from typing import Dict, Optional
from urllib.parse import urljoin

import html2text
import httpx
from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool
from bs4 import BeautifulSoup


async def fetch_webpage(
    url: str, include_images: bool = True, max_length: Optional[int] = None, headers: Optional[Dict[str, str]] = None
) -> str:
    """Fetch a webpage and convert it to markdown format.

    Args:
        url: The URL of the webpage to fetch
        include_images: Whether to include image references in the markdown
        max_length: Maximum length of the output markdown (if None, no limit)
        headers: Optional HTTP headers for the request

    Returns:
        str: Markdown version of the webpage content

    Raises:
        ValueError: If the URL is invalid or the page can't be fetched
    """
    # Use default headers if none provided
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        # Fetch the webpage
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
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

            # Configure HTML to Markdown converter
            h2t = html2text.HTML2Text()
            h2t.body_width = 0  # No line wrapping
            h2t.ignore_images = not include_images
            h2t.ignore_emphasis = False
            h2t.ignore_links = False
            h2t.ignore_tables = False

            # Convert to markdown
            markdown = h2t.handle(str(soup))

            # Trim if max_length is specified
            if max_length and len(markdown) > max_length:
                markdown = markdown[:max_length] + "\n...(truncated)"

            return markdown.strip()

    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch webpage: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Error processing webpage: {str(e)}") from e


# Create the webpage fetching tool
fetch_webpage_tool = FunctionTool(
    func=fetch_webpage,
    description="Fetch a webpage and convert it to markdown format, with options for including images and limiting length",
    global_imports=[
        "os",
        "html2text",
        ImportFromModule("typing", ("Optional", "Dict")),
        "httpx",
        ImportFromModule("bs4", ("BeautifulSoup",)),
        ImportFromModule("html2text", ("HTML2Text",)),
        ImportFromModule("urllib.parse", ("urljoin",)),
    ],
)
