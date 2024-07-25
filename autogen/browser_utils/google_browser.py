from typing import Any, Dict, List, Optional, Union, overload
from urllib.parse import urljoin, urlparse

import requests

from .base_browser import TextBrowserBase


class GoogleTextBrowser(TextBrowserBase):
    """(In preview) An extremely simple text-based web browser comparable to Lynx. Suitable for Agentic use."""

    def __init__(
        self,
        start_page: Optional[str] = None,
        viewport_size: Optional[int] = 1024 * 8,
        downloads_folder: Optional[Union[str, None]] = None,
        base_url: str = "https://customsearch.googleapis.com/customsearch/v1",
        api_key: Optional[Union[str, None]] = None,
        # Programmable Search Engines ID by Google
        cx: str = None,
        request_kwargs: Optional[Union[Dict[str, Any], None]] = None,
    ):
        super().__init__(start_page, viewport_size, downloads_folder, base_url, api_key, request_kwargs)
        self.cx = cx
        self.name = 'google'

    def set_address(self, uri_or_path: str) -> None:
        self.history.append(uri_or_path)

        # Handle special URIs
        if uri_or_path == "about:blank":
            self._set_page_content("")
        elif uri_or_path.startswith("google:"):
            print("$$$$$$$$$$$$$$$$$$$$$$$")
            self._google_search(uri_or_path[len("google:") :].strip())
        else:
            if not uri_or_path.startswith("http:") and not uri_or_path.startswith("https:"):
                uri_or_path = urljoin(self.address, uri_or_path)
                self.history[-1] = uri_or_path  # Update the address with the fully-qualified path
            self._fetch_page(uri_or_path)

        self.viewport_current_page = 0

    def _google_api_call(self, query: str) -> Dict[str, Dict[str, List[Dict[str, Union[str, Dict[str, str]]]]]]:
        # Make sure the key was set
        if self.api_key is None:
            raise ValueError("Missing Google API key.")

        # Prepare the request parameters
        request_kwargs = self.request_kwargs.copy() if self.request_kwargs is not None else {}

        if "params" not in request_kwargs:
            request_kwargs["params"] = {}
        request_kwargs["params"]["q"] = query
        request_kwargs["params"]["cx"] = self.cx
        request_kwargs["params"]["key"] = self.api_key

        # Make the request
        response = requests.get(self.base_url, **request_kwargs)
        response.raise_for_status()
        results = response.json()

        return results  # type: ignore[no-any-return]

    def _google_search(self, query: str) -> None:
        results = self._google_api_call(query)
        news_snippets = list()

        web_snippets: List[str] = list()
        idx = 0
        for page in results["items"]:
            idx += 1
            web_snippets.append(f"{idx}. [{page['title']}]({page['link']})\n{page['snippet']}")

        self.page_title = f"{query} - Search"

        content = (
            f"A Google search for '{query}' found {len(web_snippets) + len(news_snippets)} results:\n\n## Web Results\n"
            + "\n\n".join(web_snippets)
        )
        if len(news_snippets) > 0:
            content += "\n\n## News Results:\n" + "\n\n".join(news_snippets)
        self._set_page_content(content)
        results = self._google_api_call(query)

        web_snippets: List[str] = list()
        idx = 0
        for page in results["items"]:
            idx += 1
            web_snippets.append(f"{idx}. [{page['title']}]({page['link']})\n{page['snippet']}")
            if "deepLinks" in page:
                for dl in page["deepLinks"]:
                    idx += 1
                    web_snippets.append(
                        f"{idx}. [{dl['title']}]({dl['link']})\n{dl['snippet'] if 'snippet' in dl else ''}"  # type: ignore[index]
                    )

        news_snippets = list()
        if "news" in results:
            for page in results["news"]:
                idx += 1
                news_snippets.append(f"{idx}. [{page['title']}]({page['link']})\n{page['description']}")

        self.page_title = f"{query} - Search"

        content = (
            f"A Google search for '{query}' found {len(web_snippets) + len(news_snippets)} results:\n\n## Web Results\n"
            + "\n\n".join(web_snippets)
        )
        if len(news_snippets) > 0:
            content += "\n\n## News Results:\n" + "\n\n".join(news_snippets)
        self._set_page_content(content)
