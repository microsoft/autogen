import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from typing import Optional, Union, Dict

from autogen.browser_utils.abstract_browser import AbstractBrowser

# Optional PDF support
IS_PDF_CAPABLE = False
try:
    import pdfminer
    import pdfminer.high_level

    IS_PDF_CAPABLE = True
except ModuleNotFoundError:
    pass

# Other optional dependencies
try:
    import pathvalidate
except ModuleNotFoundError:
    pass


class HeadlessChromeBrowser(AbstractBrowser):
    """(In preview) A Selenium powered headless Chrome browser. Suitable for Agentic use."""

    def __init__(
        self,
        start_page: Optional[str] = "about:blank",
        viewport_size: Optional[int] = 1024 * 8,
        downloads_folder: Optional[Union[str, None]] = None,
        bing_api_key: Optional[Union[str, None]] = None,
        request_kwargs: Optional[Union[Dict, None]] = None,
    ):
        self.start_page = start_page
        self.driver = None
        self.viewport_size = viewport_size  # Applies only to the standard uri types
        self.downloads_folder = downloads_folder
        self.history = list()
        self.page_title = None
        self.viewport_current_page = 0
        self.viewport_pages = list()
        self.bing_api_key = bing_api_key
        self.request_kwargs = request_kwargs
        self._page_content = ""

        self._start_browser()

    def _start_browser(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get(self.start_page)

    @property
    def address(self) -> str:
        return self.driver.current_url

    def set_address(self, uri_or_path):
        if uri_or_path.startswith("bing:"):
            self._bing_search(uri_or_path[len("bing:") :].strip())
        else:
            self.driver.get(uri_or_path)

    @property
    def viewport(self) -> str:
        """Return the content of the current viewport."""
        if not self.viewport_pages:
            return ""
        bounds = self.viewport_pages[self.viewport_current_page]
        return self._page_content[bounds[0] : bounds[1]]

    @property
    def page_content(self) -> str:
        """Return the full contents of the current page."""
        return self._page_content

    def _set_page_content(self, content) -> str:
        """Sets the text content of the current page."""
        self._page_content = content
        self._split_pages()
        if self.viewport_current_page >= len(self.viewport_pages):
            self.viewport_current_page = len(self.viewport_pages) - 1

    def _split_pages(self):
        # Split only regular pages
        if not self.address.startswith("http:") and not self.address.startswith("https:"):
            return

        # Handle empty pages
        if len(self._page_content) == 0:
            self.viewport_pages = [(0, 0)]
            return

        # Break the viewport into pages
        self.viewport_pages = []
        start_idx = 0
        while start_idx < len(self._page_content):
            end_idx = min(start_idx + self.viewport_size, len(self._page_content))
            self.viewport_pages.append((start_idx, end_idx))
            start_idx = end_idx

    def _process_html(self, html: str) -> str:
        """Process the raw HTML content and return the processed text."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove javascript and style blocks
        for script in soup(["script", "style"]):
            script.extract()

        # Convert to text
        text = soup.get_text()

        # Remove excessive blank lines
        text = re.sub(r"\n{2,}", "\n\n", text).strip()

        return text

    def _bing_search(self, query):
        self.driver.get("https://www.bing.com")

        search_bar = self.driver.find_element(By.NAME, "q")
        search_bar.clear()
        search_bar.send_keys(query)
        search_bar.submit()

    def page_down(self):
        """Move the viewport one page down."""
        if self.viewport_current_page < len(self.viewport_pages) - 1:
            self.viewport_current_page += 1

    def page_up(self):
        """Move the viewport one page up."""
        if self.viewport_current_page > 0:
            self.viewport_current_page -= 1

    def visit_page(self, path_or_uri):
        """Update the address, visit the page, and return the content of the viewport."""
        self.set_address(path_or_uri)
        html = self.driver.execute_script("return document.body.innerHTML;")
        self._set_page_content(self._process_html(html))
        return self.viewport
