# ruff: noqa: E722
import datetime
import html
import io
import os
import pathlib
import re
import time
from typing import List, Optional, Tuple, Union

# TODO: Fix unfollowed import
from markitdown import FileConversionException, MarkItDown, UnsupportedFormatException  # type: ignore


class MarkdownFileBrowser:
    """
    (In preview) An extremely simple Markdown-powered file browser.
    """

    # TODO: Fix unfollowed import
    def __init__(  # type: ignore
        self, viewport_size: Union[int, None] = 1024 * 8
    ):
        """
        Instantiate a new RequestsMarkdownBrowser.

        Arguments:
            viewport_size: Approximately how many *characters* fit in the viewport. Viewport dimensions are adjusted dynamically to avoid cutting off words (default: 8192).
            downloads_folder: Path to where downloads are saved. If None, downloads are disabled. (default: cwd)
        """
        self.viewport_size = viewport_size  # Applies only to the standard uri types
        self.history: List[Tuple[str, float]] = list()
        self.page_title: Optional[str] = None
        self.viewport_current_page = 0
        self.viewport_pages: List[Tuple[int, int]] = list()
        self._markdown_converter = MarkItDown()
        self.set_address(os.getcwd())
        self._page_content: str = ""
        self._find_on_page_query: Union[str, None] = None
        self._find_on_page_last_result: Union[int, None] = None  # Location of the last result

    @property
    def address(self) -> str:
        """Return the address of the current page."""
        return self.history[-1][0]

    def set_address(self, path: str) -> None:
        """Sets the address of the current page.
        This will result in the file being opened for reading.

        Arguments:
            path: The fully-qualified URI to fetch, or the path to fetch from the current location. If the URI protocol is `search:`, the remainder of the URI is interpreted as a search query, and a web search is performed. If the URI protocol is `file://`, the remainder of the URI is interpreted as a local absolute file path.
        """
        self.history.append((path, time.time()))
        self._read_file(path)
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

    def open_file(self, path: str) -> str:
        """Open a file or directory in the file surfer."""
        full_path = os.path.abspath(os.path.expanduser(path))
        self.set_address(full_path)
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

    def _read_file(
        self,
        path: str,
    ) -> None:
        """Open a file for reading, converting it to Markdown in the process.

        Arguments:
            path: The path of the file or directory to open.
        """
        try:
            if os.path.isdir(path):  # TODO: Fix markdown_converter types
                res = self._markdown_converter.convert_stream(  # type: ignore
                    io.StringIO(self._fetch_local_dir(path)), file_extension=".html"
                )
                self.page_title = res.title
                self._set_page_content(res.text_content, split_pages=False)
            else:
                res = self._markdown_converter.convert_local(path)
                self.page_title = res.title
                self._set_page_content(res.text_content)
        except UnsupportedFormatException:
            self.page_title = "UnsupportedFormatException"
            self._set_page_content(f"# Cannot preview '{path}' as Markdown.")
        except FileConversionException:
            self.page_title = "FileConversionException."
            self._set_page_content(f"# Error converting '{path}' to Markdown.")
        except FileNotFoundError:
            self.page_title = "FileNotFoundError"
            self._set_page_content(f"# File not found: {path}")

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
