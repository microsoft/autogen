import ipaddress
import socket
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

import html2text
import httpx
from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool
from bs4 import BeautifulSoup

_BLOCKED_IPV4 = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("0.0.0.0/8"),
]
_BLOCKED_IPV6 = [
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _validate_url(url: str) -> None:
    """Raise ValueError if url resolves to a private/reserved IP address."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme {parsed.scheme!r} is not allowed. Only http and https are supported.")
    if not parsed.hostname:
        raise ValueError(f"URL has no hostname: {url!r}")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve hostname {parsed.hostname!r}: {exc}") from exc
    for _family, _, _, _, sockaddr in infos:
        try:
            addr = ipaddress.ip_address(sockaddr[0])
            if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
                addr = addr.ipv4_mapped
            nets = _BLOCKED_IPV4 if isinstance(addr, ipaddress.IPv4Address) else _BLOCKED_IPV6
            if any(addr in net for net in nets):
                raise ValueError(f"URL {url!r} resolves to private/reserved IP address {addr}.")
        except ValueError:
            raise


async def fetch_webpage(
    url: str, include_images: bool = True, max_length: Optional[int] = None, headers: Optional[Dict[str, str]] = None
) -> str:
    """Fetch a webpage and convert it to markdown format.

    Args:
        url: The URL of the webpage to fetch. Must resolve to a public IP address.
        include_images: Whether to include image references in the markdown
        max_length: Maximum length of the output markdown (if None, no limit)
        headers: Optional HTTP headers for the request

    Returns:
        str: Markdown version of the webpage content

    Raises:
        ValueError: If the URL is invalid, resolves to a private address, or the page can't be fetched
    """
    _validate_url(url)

    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(url, headers=headers, timeout=10)

            # Validate redirect target before following
            if response.is_redirect:
                location = response.headers.get("location", "")
                _validate_url(location)
                response = await client.get(location, headers=headers, timeout=10)

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for script in soup(["script", "style"]):
                script.decompose()

            for tag in soup.find_all(["a", "img"]):
                if tag.get("href"):
                    tag["href"] = urljoin(url, tag["href"])
                if tag.get("src"):
                    tag["src"] = urljoin(url, tag["src"])

            h2t = html2text.HTML2Text()
            h2t.body_width = 0
            h2t.ignore_images = not include_images
            h2t.ignore_emphasis = False
            h2t.ignore_links = False
            h2t.ignore_tables = False

            markdown = h2t.handle(str(soup))

            if max_length and len(markdown) > max_length:
                markdown = markdown[:max_length] + "\n...(truncated)"

            return markdown.strip()

    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch webpage: {str(e)}") from e
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Error processing webpage: {str(e)}") from e


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
