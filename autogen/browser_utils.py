import json
import requests
import re
import markdownify
import io
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Callable, Literal, Tuple

IS_PDF_CAPABLE = False
try:
    import pdfminer
    import pdfminer.high_level

    IS_PDF_CAPABLE = True
except ModuleNotFoundError:
    pass


class SimpleTextBrowser:
    """(In preview) An extremely simple text-based web browser comparable to Lynx. Suitable for Agentic use."""

    def __init__(
        self,
        start_page: Optional[str] = "about:blank",
        viewport_size: Optional[int] = 2048,
        downloads_folder: Optional[Union[str, None]] = None,
        bing_api_key: Optional[Union[str, None]] = None,
    ):
        self.start_page = start_page
        self.viewport_size = viewport_size  # Applies only to the standard uri types
        self.downloads_folder = downloads_folder
        self.history = list()
        self.page_title = None
        self.page_content = ""
        self.viewport_position = 0
        self.set_address(start_page)
        self.bing_api_key = bing_api_key

        # For find on page
        self.find_string = ""
        self.find_matches = list()
        self.find_idx = 0

    @property
    def address(self) -> str:
        """Return the address of the current page."""
        return self.history[-1]

    def set_address(self, uri_or_path):
        # Handle special URIs
        if uri_or_path == "about:blank":
            self.page_content = list()
        elif uri_or_path.startswith("bing:"):
            self._bing_search(uri_or_path[len("bing:") :].strip())
        else:
            if not uri_or_path.startswith("http:") and not uri_or_path.startswith("https:"):
                uri_or_path = urljoin(self.address, uri_or_path)
            self._fetch_page(uri_or_path)

        self.history.append(uri_or_path)
        self.viewport_position = 0
        self.find_string = ""
        self.find_matches = list()
        self.find_idx = 0

    @property
    def viewport(self) -> str:
        """Return the content of the current viewport."""
        if self.address.startswith("http:") or self.address.startswith("https:"):
            start_idx = self._viewport_start_position()
            end_idx = self._viewport_end_position()
            return self.page_content[start_idx:end_idx]
        else:
            return self.page_content

    def _viewport_start_position(self) -> int:
        start_idx = max(self.viewport_position, 0)
        while start_idx > 0 and self.page_content[start_idx] not in [" ", "\t", "\r", "\n"]:
            start_idx -= 1
        return start_idx

    def _viewport_end_position(self) -> int:
        end_idx = min(self.viewport_position + self.viewport_size, len(self.page_content))
        while end_idx < len(self.page_content) and self.page_content[end_idx - 1] not in [" ", "\t", "\r", "\n"]:
            end_idx += 1
        return end_idx

    def page_down(self):
        self.viewport_position = min(self._viewport_end_position(), len(self.page_content) - 1)

    def page_up(self):
        self.viewport_position -= self.viewport_size
        self.viewport_position = self._viewport_start_position()  # Align to whitespace

    def find_on_page(self, string):
        self.find_string = string
        self.find_matches = [m.start() for m in re.finditer(re.escape(string), self.page_content, re.IGNORECASE)]
        self.find_idx = -1
        return self.find_next_on_page()

    def find_next_on_page(self):
        if len(self.find_matches) == 0:
            return False
        self.find_idx += 1
        if self.find_idx >= len(self.find_matches):
            self.find_idx = 0  # Loop around

        # Scroll to the position
        self.viewport_position = self.find_matches[self.find_idx] - 100  # Context
        self.viewport_position = self._viewport_start_position()  # Align to whitespace
        return True

    def visit_page(self, path_or_uri):
        """Update the address, visit the page, and return the content of the viewport."""
        self.set_address(path_or_uri)
        return self.viewport

    def _bing_search(self, query):
        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        params = {"q": query, "textDecorations": False, "textFormat": "raw"}
        response = requests.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params)
        response.raise_for_status()
        results = response.json()

        web_snippets = list()
        idx = 0
        for page in results["webPages"]["value"]:
            idx += 1
            web_snippets.append(f"{idx}. [{page['name']}]({page['url']})\n{page['snippet']}")
            if "deepLinks" in page:
                for dl in page["deepLinks"]:
                    idx += 1
                    web_snippets.append(
                        f"{idx}. [{dl['name']}]({dl['url']})\n{dl['snippet'] if 'snippet' in dl else ''}"
                    )

        news_snippets = list()
        if "news" in results:
            for page in results["news"]["value"]:
                idx += 1
                news_snippets.append(f"{idx}. [{page['name']}]({page['url']})\n{page['description']}")

        self.page_title = f"{query} - Search"
        self.page_content = (
            f"A Bing search for '{query}' found {len(web_snippets) + len(news_snippets)} results:\n\n## Web Results\n"
            + "\n\n".join(web_snippets)
        )
        if len(news_snippets) > 0:
            self.page_content += "\n\n## News Results:\n" + "\n\n".join(news_snippets)

    def _fetch_page(self, url):
        try:
            # Send a HTTP request to the URL
            response = requests.get(url, stream=True)
            response.raise_for_status()

            # If the HTTP request returns a status code 200, proceed
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                for ct in ["text/html", "text/plain", "application/pdf"]:
                    if ct in content_type.lower():
                        content_type = ct
                        break

                if content_type == "text/html":
                    # Get the content of the response
                    html = ""
                    for chunk in response.iter_content(decode_unicode=True):
                        html += chunk

                    soup = BeautifulSoup(html, "html.parser")

                    # Remove javascript and style blocks
                    for script in soup(["script", "style"]):
                        script.extract()

                    # Convert to markdown
                    webpage_text = markdownify.MarkdownConverter().convert_soup(soup)

                    # Convert newlines
                    webpage_text = re.sub(r"\r\n", "\n", webpage_text)

                    # Remove excesive blank lines
                    self.page_title = soup.title.string
                    self.page_content = re.sub(r"\n{2,}", "\n\n", webpage_text).strip()
                elif content_type == "text/plain":
                    # Get the content of the response
                    plain_text = ""
                    for chunk in response.iter_content(decode_unicode=True):
                        plain_text += chunk

                    self.page_title = None
                    self.page_content = plain_text
                elif IS_PDF_CAPABLE and content_type == "application/pdf":
                    pdf_data = io.BytesIO(response.raw.read())
                    self.page_title = None
                    self.page_content = pdfminer.high_level.extract_text(pdf_data)
                else:
                    self.page_title = f"Error - Unsupported Content-Type '{content_type}'"
                    self.page_content = self.page_title
            else:
                self.page_title = "Error"
                self.page_content = "Failed to retrieve " + url
        except requests.exceptions.RequestException as e:
            self.page_title = "Error"
            self.page_content = str(e)


if __name__ == "__main__":
    import os

    browser = SimpleTextBrowser(bing_api_key=os.environ["BING_API_KEY"])

    # print(browser.visit_page("bing: latest news on OpenAI"))
    # input("Press Next to navigate to Micosoft wikipedia page...")
    print(browser.visit_page("https://www.adamfourney.com/papers/bibtex/chang_arxiv2023.txt"))
    input("Press Enter to fetch PDF...")
    print(browser.visit_page("https://arxiv.org/pdf/2306.04930.pdf"))
    input("Press Enter to visit Wikipedia...")
    print(browser.visit_page("https://en.wikipedia.org/wiki/Microsoft"))
    input("Press Next to find on the page...")
    browser.find_on_page("Bill Gates")
    print(browser.viewport)
    input("Press Next to navigate to Apple...")
    print(browser.visit_page("Apple_Inc."))
    input("Press Enter to continue down...")
    browser.page_down()
    print(browser.viewport)
    input("Press Enter to continue down...")
    browser.page_down()
    print(browser.viewport)
    input("Press Enter to continue up...")
    browser.page_up()
    print(browser.viewport)
