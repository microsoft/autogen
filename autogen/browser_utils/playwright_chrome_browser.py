import re
import os
import pathlib
import io
import time
import html
import datetime
from typing import Optional, Union, Dict

from urllib.parse import urljoin, urlparse, unquote, parse_qs
from urllib.request import url2pathname

from autogen.browser_utils.abstract_browser import AbstractBrowser
from autogen.browser_utils.mdconvert import MarkdownConverter, UnsupportedFormatException, FileConversionException

# Check if Playwright dependencies are installed
IS_PLAYWRIGHT_ENABLED = False
try:
    from playwright.sync_api import sync_playwright
    from playwright._impl._errors import TimeoutError

    IS_PLAYWRIGHT_ENABLED = True
except ModuleNotFoundError:
    pass


class PlaywrightChromeBrowser(AbstractBrowser):
    """(In preview) A Selenium powered headless Chrome browser. Suitable for Agentic use."""

    def __init__(
        self,
        start_page: Optional[str] = "about:blank",
        viewport_size: Optional[int] = 1024 * 8,
        downloads_folder: Optional[Union[str, None]] = None,
        bing_api_key: Optional[Union[str, None]] = None,
        request_kwargs: Optional[Union[Dict, None]] = None,
    ):
        self._browser = None
        self._playwright = None

        # Raise an error if Playwright isn't available
        if not IS_PLAYWRIGHT_ENABLED:
            raise ModuleNotFoundError(
                "No module named 'playwright'. Playwright can be installed via 'pip install playwright' or 'conda install playwright' depending on your environment."
            )

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
        self._mdconvert = MarkdownConverter()

        # Create the playwright instance
        self._playwright = sync_playwright().start()
        if downloads_folder is not None and downloads_folder.strip() != "":
            self._browser = self._playwright.chromium.launch_persistent_context(
                accept_downloads=True, user_data_dir=downloads_folder
            )
        else:
            self._browser = self._playwright.chromium.launch_persistent_context()

        # Browser context
        self._page = self._browser.new_page()
        self.set_address(self.start_page)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    @property
    def address(self) -> str:
        """Return the address of the current page."""
        return self.history[-1][0]

    def set_address(self, uri_or_path: str) -> None:
        # TODO: Handle anchors
        self.history.append((uri_or_path, time.time()))

        # Handle special URIs
        if uri_or_path == "about:blank":
            self._set_page_content("")
        elif uri_or_path.startswith("bing:"):
            self._bing_search(uri_or_path[len("bing:") :].strip())
        else:
            if (
                not uri_or_path.startswith("http:")
                and not uri_or_path.startswith("https:")
                and not uri_or_path.startswith("file:")
            ):
                if len(self.history) > 1:
                    prior_address = self.history[-2][0]
                    uri_or_path = urljoin(prior_address, uri_or_path)
                    # Update the address with the fully-qualified path
                    self.history[-1] = (uri_or_path, self.history[-1][1])
            self._fetch_page(uri_or_path)

        self.viewport_current_page = 0
        self.find_on_page_query = None
        self.find_on_page_viewport = None

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

    def _set_page_content(self, content: str, split_pages=True) -> None:
        """Sets the text content of the current page."""
        self._page_content = content

        if split_pages:
            self._split_pages()
        else:
            self.viewport_pages = [(0, len(self._page_content))]

        if self.viewport_current_page >= len(self.viewport_pages):
            self.viewport_current_page = len(self.viewport_pages) - 1

    def _split_pages(self) -> None:
        # Handle empty pages
        if len(self._page_content) == 0:
            self.viewport_pages = [(0, 0)]
            return

        # Break the viewport into pages
        self.viewport_pages = []
        start_idx = 0
        while start_idx < len(self._page_content):
            end_idx = min(start_idx + self.viewport_size, len(self._page_content))  # type: ignore[operator]
            # Adjust to end on a space
            while end_idx < len(self._page_content) and self._page_content[end_idx - 1] not in [" ", "\t", "\r", "\n"]:
                end_idx += 1
            self.viewport_pages.append((start_idx, end_idx))
            start_idx = end_idx

    def _bing_search(self, query):
        raise NotImplementedError()

    def page_down(self):
        """Move the viewport one page down."""
        if self.viewport_current_page < len(self.viewport_pages) - 1:
            self.viewport_current_page += 1

    def page_up(self):
        """Move the viewport one page up."""
        if self.viewport_current_page > 0:
            self.viewport_current_page -= 1

    def find_on_page(self, query: str):
        raise NotImplementedError()

    def find_next(self):
        raise NotImplementedError()

    def visit_page(self, path_or_uri: str) -> str:
        """Update the address, visit the page, and return the content of the viewport."""
        self.set_address(path_or_uri)
        return self.viewport

    def open_local_file(self, local_path: str) -> str:
        """Convert a local file path to a file:/// URI, update the address, visit the page,
        and return the contents of the viewport."""
        full_path = os.path.abspath(os.path.expanduser(local_path))
        self.set_address(pathlib.Path(full_path).as_uri())
        return self.viewport

    def _fetch_page(self, url) -> None:
        if url.startswith("file://"):
            download_path = os.path.normcase(os.path.normpath(unquote(url[7:])))
            if os.path.isdir(download_path):
                res = self._mdconvert.convert_stream(
                    io.StringIO(self._fetch_local_dir(download_path)), file_extension=".html"
                )
                self.page_title = res.title
                self._set_page_content(
                    res.text_content, split_pages=False
                )  # Like search results, don't split directory listings
            else:
                res = self._mdconvert.convert_local(download_path, url=url)
                self.page_title = res.title
                self._set_page_content(res.text_content)
        else:
            try:
                self._page.goto(url)
                return self._process_page(url, self._page)
            except Exception as e:
                if "net::ERR_ABORTED" in str(e):
                    with self._page.expect_download() as download_info:
                        try:
                            self._page.goto(url)
                        except Exception as e:
                            if "net::ERR_ABORTED" in str(e):
                                pass
                            else:
                                raise (e)
                        download = download_info.value
                        fname = "./" + download.suggested_filename
                        download.save_as(fname)
                        self._process_download(download.url, fname)
                else:
                    raise (e)

    def _process_page(self, url, page):
        body = self._page.query_selector("body")
        html = body.inner_html()
        res = self._mdconvert.convert_stream(io.StringIO(html), file_extension=".html", url=url)
        self.page_title = res.title
        self._set_page_content(res.text_content)

    def _process_download(self, url, path):
        res = self._mdconvert.convert_local(path, url=url)
        self.page_title = res.title
        self._set_page_content(res.text_content)

    def _fetch_local_dir(self, local_path: str) -> str:
        pardir = os.path.normpath(os.path.join(local_path, os.pardir))
        pardir_uri = pathlib.Path(pardir).as_uri()
        listing = f"""
<!DOCTYPE html>
<html>
  <head>
    <title>Index of {html.escape(local_path)}</title>
  </head>
  <body>
    <h1>Index of {html.escape(local_path)}</h1>

    <a href="{html.escape(pardir_uri, quote=True)}">.. (parent directory)</a>

    <table>
    <tr>
       <th>Name</th><th>Size</th><th>Date modified</th>
    </tr>
"""

        for entry in os.listdir(local_path):
            full_path = os.path.normpath(os.path.join(local_path, entry))
            full_path_uri = pathlib.Path(full_path).as_uri()
            size = ""
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M")

            if os.path.isdir(full_path):
                entry = entry + os.path.sep
            else:
                size = str(os.path.getsize(full_path))

            listing += (
                "<tr>\n"
                + f'<td><a href="{html.escape(full_path_uri, quote=True)}">{html.escape(entry)}</a></td>'
                + f"<td>{html.escape(size)}</td>"
                + f"<td>{html.escape(mtime)}</td>"
                + "</tr>"
            )

        listing += """
    </table>
  </body>
</html>
"""
        return listing
