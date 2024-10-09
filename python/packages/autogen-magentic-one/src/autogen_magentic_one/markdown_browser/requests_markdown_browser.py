# ruff: noqa: E722
import datetime
import html
import io
import mimetypes
import os
import pathlib
import re
import time
import traceback
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote, urljoin, urlparse

import pathvalidate
import requests

from .abstract_markdown_browser import AbstractMarkdownBrowser
from .markdown_search import AbstractMarkdownSearch, BingMarkdownSearch

# TODO: Fix unfollowed import
from .mdconvert import FileConversionException, MarkdownConverter, UnsupportedFormatException  # type: ignore


class RequestsMarkdownBrowser(AbstractMarkdownBrowser):
    """
    (In preview) An extremely simple Python requests-powered Markdown web browser.
    This browser cannot run JavaScript, compute CSS, etc. It simply fetches the HTML document, and converts it to Markdown.
    See AbstractMarkdownBrowser for more details.
    """

    # TODO: Fix unfollowed import
    def __init__(  # type: ignore
        self,
        start_page: Union[str, None] = None,
        viewport_size: Union[int, None] = 1024 * 8,
        downloads_folder: Union[str, None] = None,
        search_engine: Union[AbstractMarkdownSearch, None] = None,
        markdown_converter: Union[MarkdownConverter, None] = None,
        requests_session: Union[requests.Session, None] = None,
        requests_get_kwargs: Union[Dict[str, Any], None] = None,
    ):
        """
        Instantiate a new RequestsMarkdownBrowser.

        Arguments:
            start_page: The page on which the browser starts (default: "about:blank")
            viewport_size: Approximately how many *characters* fit in the viewport. Viewport dimensions are adjusted dynamically to avoid cutting off words (default: 8192).
            downloads_folder: Path to where downloads are saved. If None, downloads are disabled. (default: None)
            search_engine: An instance of MarkdownSearch, which handles web searches performed by this browser (default: a new `BingMarkdownSearch()` with default parameters)
            markdown_converted: An instance of a MarkdownConverter used to convert HTML pages and downloads to Markdown (default: a new `MarkdownConerter()` with default parameters)
            request_session: The session from which to issue requests (default: a new `requests.Session()` instance with default parameters)
            request_get_kwargs: Extra parameters passed to evert `.get()` call made to requests.
        """
        self.start_page: str = start_page if start_page else "about:blank"
        self.viewport_size = viewport_size  # Applies only to the standard uri types
        self.downloads_folder = downloads_folder
        self.history: List[Tuple[str, float]] = list()
        self.page_title: Optional[str] = None
        self.viewport_current_page = 0
        self.viewport_pages: List[Tuple[int, int]] = list()
        self.set_address(self.start_page)
        self._page_content: str = ""

        if search_engine is None:
            self._search_engine: AbstractMarkdownSearch = BingMarkdownSearch()
        else:
            self._search_engine = search_engine

        if markdown_converter is None:
            self._markdown_converter = MarkdownConverter()
        else:
            self._markdown_converter = markdown_converter

        if requests_session is None:
            self._requests_session = requests.Session()
        else:
            self._requests_session = requests_session

        if requests_get_kwargs is None:
            self._requests_get_kwargs = {}
        else:
            self._requests_get_kwargs = requests_get_kwargs

        self._find_on_page_query: Union[str, None] = None
        self._find_on_page_last_result: Union[int, None] = None  # Location of the last result

    @property
    def address(self) -> str:
        """Return the address of the current page."""
        return self.history[-1][0]

    def set_address(self, uri_or_path: str) -> None:
        """Sets the address of the current page.
        This will result in the page being fetched via the underlying requests session.

        Arguments:
            uri_or_path: The fully-qualified URI to fetch, or the path to fetch from the current location. If the URI protocol is `search:`, the remainder of the URI is interpreted as a search query, and a web search is performed. If the URI protocol is `file://`, the remainder of the URI is interpreted as a local absolute file path.
        """
        # TODO: Handle anchors
        self.history.append((uri_or_path, time.time()))

        # Handle special URIs
        if uri_or_path == "about:blank":
            self._set_page_content("")
        elif uri_or_path.startswith("search:"):
            query = uri_or_path[len("search:") :].strip()
            results = self._search_engine.search(query)
            self.page_title = f"{query} - Search"
            self._set_page_content(results, split_pages=False)
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
        bounds = self.viewport_pages[self.viewport_current_page]
        return self.page_content[bounds[0] : bounds[1]]

    @property
    def page_content(self) -> str:
        """Return the full contents of the current page."""
        return self._page_content

    def _set_page_content(self, content: str, split_pages: bool = True) -> None:
        """Sets the text content of the current page."""
        self._page_content = content

        if split_pages:
            self._split_pages()
        else:
            self.viewport_pages = [(0, len(self._page_content))]

        if self.viewport_current_page >= len(self.viewport_pages):
            self.viewport_current_page = len(self.viewport_pages) - 1

    def page_down(self) -> None:
        """Move the viewport down one page, if possible."""
        self.viewport_current_page = min(self.viewport_current_page + 1, len(self.viewport_pages) - 1)

    def page_up(self) -> None:
        """Move the viewport up one page, if possible."""
        self.viewport_current_page = max(self.viewport_current_page - 1, 0)

    def find_on_page(self, query: str) -> Union[str, None]:
        """Searches for the query from the current viewport forward, looping back to the start if necessary."""

        # Did we get here via a previous find_on_page search with the same query?
        # If so, map to find_next
        if query == self._find_on_page_query and self.viewport_current_page == self._find_on_page_last_result:
            return self.find_next()

        # Ok it's a new search start from the current viewport
        self._find_on_page_query = query
        viewport_match = self._find_next_viewport(query, self.viewport_current_page)
        if viewport_match is None:
            self._find_on_page_last_result = None
            return None
        else:
            self.viewport_current_page = viewport_match
            self._find_on_page_last_result = viewport_match
            return self.viewport

    def find_next(self) -> Union[str, None]:
        """Scroll to the next viewport that matches the query"""

        if self._find_on_page_query is None:
            return None

        starting_viewport = self._find_on_page_last_result
        if starting_viewport is None:
            starting_viewport = 0
        else:
            starting_viewport += 1
            if starting_viewport >= len(self.viewport_pages):
                starting_viewport = 0

        viewport_match = self._find_next_viewport(self._find_on_page_query, starting_viewport)
        if viewport_match is None:
            self._find_on_page_last_result = None
            return None
        else:
            self.viewport_current_page = viewport_match
            self._find_on_page_last_result = viewport_match
            return self.viewport

    def _find_next_viewport(self, query: Optional[str], starting_viewport: int) -> Union[int, None]:
        """Search for matches between the starting viewport looping when reaching the end."""

        if query is None:
            return None

        # Normalize the query, and convert to a regular expression
        nquery = re.sub(r"\*", "__STAR__", query)
        nquery = " " + (" ".join(re.split(r"\W+", nquery))).strip() + " "
        nquery = nquery.replace(" __STAR__ ", "__STAR__ ")  # Merge isolated stars with prior word
        nquery = nquery.replace("__STAR__", ".*").lower()

        if nquery.strip() == "":
            return None

        idxs: List[int] = list()
        idxs.extend(range(starting_viewport, len(self.viewport_pages)))
        idxs.extend(range(0, starting_viewport))

        for i in idxs:
            bounds = self.viewport_pages[i]
            content = self.page_content[bounds[0] : bounds[1]]

            # TODO: Remove markdown links and images
            ncontent = " " + (" ".join(re.split(r"\W+", content))).strip().lower() + " "
            if re.search(nquery, ncontent):
                return i

        return None

    def visit_page(self, path_or_uri: str) -> str:
        """Update the address, visit the page, and return the content of the viewport."""
        self.set_address(path_or_uri)
        return self.viewport

    def open_local_file(self, local_path: str) -> str:
        """Convert a local file path to a file:/// URI, update the address, visit the page, and return the contents of the viewport."""
        full_path = os.path.abspath(os.path.expanduser(local_path))
        self.set_address(pathlib.Path(full_path).as_uri())
        return self.viewport

    def _split_pages(self) -> None:
        """Split the page contents into pages that are approximately the viewport size. Small deviations are permitted to ensure words are not broken."""
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

    def _fetch_page(
        self,
        url: str,
        session: Optional[requests.Session] = None,
        requests_get_kwargs: Union[Dict[str, Any], None] = None,
    ) -> None:
        """Fetch a page using the requests library. Then convert it to Markdown, and set `page_content` (which splits the content into pages as necessary.

        Arguments:
            url: The fully-qualified URL to fetch.
            session: Used to override the session used for this request. If None, use `self._requests_session` as usual.
            requests_get_kwargs: Extra arguments passes to `requests.Session.get`.
        """
        download_path: str = ""
        response: Union[requests.Response, None] = None
        try:
            if url.startswith("file://"):
                download_path = os.path.normcase(os.path.normpath(unquote(url[7:])))
                if os.path.isdir(download_path):  # TODO: Fix markdown_converter types
                    res = self._markdown_converter.convert_stream(  # type: ignore
                        io.StringIO(self._fetch_local_dir(download_path)), file_extension=".html"
                    )
                    self.page_title = res.title
                    self._set_page_content(
                        res.text_content, split_pages=False
                    )  # Like search results, don't split directory listings
                else:
                    res = self._markdown_converter.convert_local(download_path)
                    self.page_title = res.title
                    self._set_page_content(res.text_content)
            else:
                # Send a HTTP request to the URL
                if session is None:
                    session = self._requests_session

                _get_kwargs: Dict[str, Any] = {}  # TODO: Deal with kwargs
                _get_kwargs.update(self._requests_get_kwargs)
                if requests_get_kwargs is not None:
                    _get_kwargs.update(requests_get_kwargs)
                _get_kwargs["stream"] = True

                response = session.get(url, **_get_kwargs)
                response.raise_for_status()

                # If the HTTP request was successful
                content_type = response.headers.get("content-type", "")

                # Text or HTML
                if "text/" in content_type.lower():
                    res = self._markdown_converter.convert_response(response)
                    self.page_title = res.title
                    self._set_page_content(res.text_content)
                # A download
                else:
                    # Was a downloads folder configured?
                    if self.downloads_folder is None:
                        self.page_title = "Error 400"
                        self._set_page_content("## Error 400\n\nClient does not support downloads")
                        return

                    assert self.downloads_folder is not None

                    # Try producing a safe filename
                    fname: str = ""
                    try:
                        fname = pathvalidate.sanitize_filename(os.path.basename(urlparse(url).path)).strip()
                        download_path = os.path.abspath(os.path.join(self.downloads_folder, fname))

                        suffix = 0
                        while os.path.exists(download_path) and suffix < 1000:
                            suffix += 1
                            base, ext = os.path.splitext(fname)
                            new_fname = f"{base}__{suffix}{ext}"
                            download_path = os.path.abspath(os.path.join(self.downloads_folder, new_fname))

                    except NameError:
                        pass

                    # No suitable name, so make one
                    if fname == "":
                        extension = mimetypes.guess_extension(content_type)
                        if extension is None:
                            extension = ".download"
                        fname = str(uuid.uuid4()) + extension
                        download_path = os.path.abspath(os.path.join(self.downloads_folder, fname))

                    # Open a file for writing
                    with open(download_path, "wb") as fh:
                        for chunk in response.iter_content(chunk_size=512):
                            fh.write(chunk)

                    # Render it
                    local_uri = pathlib.Path(download_path).as_uri()
                    self.set_address(local_uri)

        except UnsupportedFormatException:
            self.page_title = "Download complete."
            self._set_page_content(f"# Download complete\n\nSaved file to '{download_path}'")
        except FileConversionException:
            self.page_title = "Download complete."
            self._set_page_content(f"# Download complete\n\nSaved file to '{download_path}'")
        except FileNotFoundError:
            self.page_title = "Error 404"
            self._set_page_content(f"## Error 404\n\nFile not found: {download_path}")
        except requests.exceptions.RequestException:
            if response is None:
                self.page_title = "Request Exception"
                self._set_page_content("## Unhandled Request Exception:\n\n" + traceback.format_exc())
            else:
                self.page_title = f"Error {response.status_code}"

                # If the error was rendered in HTML we might as well render it
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type.lower():
                    res = self._markdown_converter.convert(response)
                    self.page_title = f"Error {response.status_code}"
                    self._set_page_content(f"## Error {response.status_code}\n\n{res.text_content}")
                else:
                    text = ""
                    for chunk in response.iter_content(chunk_size=512, decode_unicode=True):
                        text += chunk
                    self.page_title = f"Error {response.status_code}"
                    self._set_page_content(f"## Error {response.status_code}\n\n{text}")

    def _fetch_local_dir(self, local_path: str) -> str:
        """Render a local directory listing in HTML to assist with local file browsing via the "file://" protocol.
        Through rendered in HTML, later parts of the pipeline will convert the listing to Markdown.

        Arguments:
            local_path: A path to the local directory whose contents are to be listed.

        Returns:
            A directory listing, rendered in HTML.
        """
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
