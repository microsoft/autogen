import io
import os
from typing import Dict, Optional, Union
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

from .requests_markdown_browser import RequestsMarkdownBrowser

# Check if Selenium dependencies are installed
IS_SELENIUM_ENABLED = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    IS_SELENIUM_ENABLED = True
except ModuleNotFoundError:
    pass


class SeleniumMarkdownBrowser(RequestsMarkdownBrowser):
    """
    (In preview) A Selenium and Chromium powered Markdown web browser.
    SeleniumMarkdownBrowser extends RequestsMarkdownBrowser, and replaces only the functionality of `visit_page(url)`.
    """

    def __init__(self, **kwargs):
        """
        Instantiate a new SeleniumMarkdownBrowser.

        Arguments:
            **kwargs: SeleniumMarkdownBrowser passes all arguments to the RequestsMarkdownBrowser superclass. See RequestsMarkdownBrowser documentation for more details.
        """

        super().__init__(**kwargs)
        self._webdriver = None

        # Raise an error if Playwright isn't available
        if not IS_SELENIUM_ENABLED:
            raise ModuleNotFoundError(
                "No module named 'selenium'. Selenium can be installed via 'pip install selenium' or 'conda install selenium' depending on your environment."
            )

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        self._webdriver = webdriver.Chrome(options=chrome_options)
        self._webdriver.implicitly_wait(99)
        self._webdriver.get(self.start_page)

    def __del__(self):
        """
        Close the Selenium session when garbage-collected. Garbage collection may not always occur, or may happen at a later time. Call `close()` explicitly if you wish to free up resources used by Selenium or Chromium.
        """
        self.close()

    def close(self):
        """
        Close the Selenium session used by this instance. The session cannot be reopened without instantiating a new SeleniumMarkdownBrowser instance.
        """
        if self._webdriver is not None:
            self._webdriver.quit()
            self._webdriver = None

    def _fetch_page(self, url) -> None:
        """
        Fetch a page. If the page is a regular HTTP page, use Selenium to gather the HTML. If the page is a download, or a local file, rely on superclass behavior.
        """
        if url.startswith("file://"):
            super()._fetch_page(url)
        else:
            self._webdriver.get(url)
            html = self._webdriver.execute_script("return document.documentElement.outerHTML;")

            if not html:  # Nothing... it's probably a download
                super()._fetch_page(url)
            else:
                self.page_title = self._webdriver.execute_script("return document.title;")
                res = self._markdown_converter.convert_stream(io.StringIO(html), file_extension=".html", url=url)
                self._set_page_content(res.text_content)
