import os
import io
from typing import Optional, Union, Dict, Any
from urllib.parse import urljoin, urlparse, quote_plus, unquote, parse_qs
from .requests_markdown_browser import RequestsMarkdownBrowser

# Check if Playwright dependencies are installed
IS_PLAYWRIGHT_ENABLED = False
try:
    from playwright.sync_api import sync_playwright
    from playwright._impl._errors import TimeoutError

    IS_PLAYWRIGHT_ENABLED = True
except ModuleNotFoundError:
    pass


class PlaywrightMarkdownBrowser(RequestsMarkdownBrowser):
    """
    (In preview) A Playwright and Chromium powered Markdown web browser.
    See AbstractMarkdownBrowser for more details.
    """

    def __init__(
        self,
        launch_args: Dict[str,Any] = {},
        **kwargs
    ):
        super().__init__(**kwargs)
        self._playwright = None
        self._browser = None
        self._page = None

        # Raise an error if Playwright isn't available
        if not IS_PLAYWRIGHT_ENABLED:
            raise ModuleNotFoundError(
                    "No module named 'playwright'. Playwright can be installed via 'pip install playwright' or 'conda install playwright' depending on your environment.\n\nOnce installed, you must also install a browser via 'playwright install --with-deps chromium'"
            )

        # Create the playwright instance
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(**launch_args)

        # Browser context
        self._page = self._browser.new_page()
        self.set_address(self.start_page)

    def __del__(self):
        self.close()

    def close(self):
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def _fetch_page(self, url) -> None:
        if url.startswith("file://"):
            super()._fetch_page(url)
        else:
            try:
                # Regular webpage
                self._page.goto(url)
                return self._process_page(url, self._page)
            except Exception as e:
                # Downloaded file
                if self.downloads_folder and "net::ERR_ABORTED" in str(e):
                    with self._page.expect_download() as download_info:
                        try:
                            self._page.goto(url)
                        except Exception as e:
                            if "net::ERR_ABORTED" in str(e):
                                pass
                            else:
                                raise e
                        download = download_info.value
                        fname = os.path.join(self.downloads_folder, download.suggested_filename)
                        download.save_as(fname)
                        self._process_download(url, fname)
                else:
                    raise e

    def _process_page(self, url, page):
        html = page.evaluate("document.documentElement.outerHTML;")
        res = self._markdown_converter.convert_stream(io.StringIO(html), file_extension=".html", url=url)
        self.page_title = page.title()
        self._set_page_content(res.text_content)

    def _process_download(self, url, path):
        res = self._markdown_converter.convert_local(path, url=url)
        self.page_title = res.title
        self._set_page_content(res.text_content)
