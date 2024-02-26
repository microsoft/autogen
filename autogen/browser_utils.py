# ruff: noqa: E722
import json
import os
import requests
import re
import io
import uuid
import mimetypes
import time
import pathlib
import pathvalidate
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.request import url2pathname
from typing import Any, Dict, List, Optional, Union, Tuple
from .mdconvert import MarkdownConverter, UnsupportedFormatException

class SimpleTextBrowser:
    """(In preview) An extremely simple text-based web browser comparable to Lynx. Suitable for Agentic use."""

    def __init__(
        self,
        start_page: Optional[str] = None,
        viewport_size: Optional[int] = 1024 * 8,
        downloads_folder: Optional[Union[str, None]] = None,
        bing_api_key: Optional[Union[str, None]] = None,
        request_kwargs: Optional[Union[Dict[str, Any], None]] = None,
    ):
        self.start_page: str = start_page if start_page else "about:blank"
        self.viewport_size = viewport_size  # Applies only to the standard uri types
        self.downloads_folder = downloads_folder
        self.history: List[Tuple[str, float]] = list()
        self.page_title: Optional[str] = None
        self.viewport_current_page = 0
        self.viewport_pages: List[Tuple[int, int]] = list()
        self.set_address(self.start_page)
        self.bing_api_key = bing_api_key
        self.request_kwargs = request_kwargs
        self._mdconvert = MarkdownConverter()
        self._page_content: str = ""

        self._find_on_page_query: Union[str, None] = None
        self._find_on_page_last_result: Union[int, None] = None  # Location of the last result

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
        bounds = self.viewport_pages[self.viewport_current_page]
        return self.page_content[bounds[0] : bounds[1]]

    @property
    def page_content(self) -> str:
        """Return the full contents of the current page."""
        return self._page_content

    def _set_page_content(self, content: str) -> None:
        """Sets the text content of the current page."""
        self._page_content = content
        self._split_pages()
        if self.viewport_current_page >= len(self.viewport_pages):
            self.viewport_current_page = len(self.viewport_pages) - 1

    def page_down(self) -> None:
        self.viewport_current_page = min(self.viewport_current_page + 1, len(self.viewport_pages) - 1)

    def page_up(self) -> None:
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

    def find_next(self) -> None:
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

    def _find_next_viewport(self, query: str, starting_viewport: int) -> Union[int, None]:
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

        idxs = list()
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

    def _split_pages(self) -> None:
        # Split only regular pages
        if not self.address.startswith("http:") and not self.address.startswith("https:"):
            self.viewport_pages = [(0, len(self._page_content))]
            return

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

    def _bing_api_call(self, query: str) -> Dict[str, Dict[str, List[Dict[str, Union[str, Dict[str, str]]]]]]:
        # Make sure the key was set
        if self.bing_api_key is None:
            raise ValueError("Missing Bing API key.")

        # Prepare the request parameters
        request_kwargs = self.request_kwargs.copy() if self.request_kwargs is not None else {}

        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        request_kwargs["headers"]["Ocp-Apim-Subscription-Key"] = self.bing_api_key

        if "params" not in request_kwargs:
            request_kwargs["params"] = {}
        request_kwargs["params"]["q"] = query
        request_kwargs["params"]["textDecorations"] = False
        request_kwargs["params"]["textFormat"] = "raw"

        request_kwargs["stream"] = False

        # Make the request
        response = requests.get("https://api.bing.microsoft.com/v7.0/search", **request_kwargs)
        response.raise_for_status()
        results = response.json()

        return results  # type: ignore[no-any-return]

    def _bing_search(self, query: str) -> None:
        results = self._bing_api_call(query)

        def _prev_visit(url):
            for i in range(len(self.history) - 1, -1, -1):
                if self.history[i][0] == url:
                    # Todo make this more human-friendly
                    return f"You previously visited this page {round(time.time() - self.history[i][1])} seconds ago.\n"
            return ""

        web_snippets: List[str] = list()
        idx = 0
        for page in results["webPages"]["value"]:
            idx += 1
            web_snippets.append(f"{idx}. [{page['name']}]({page['url']})\n{_prev_visit(page['url'])}{page['snippet']}")
            if "deepLinks" in page:
                for dl in page["deepLinks"]:
                    idx += 1
                    web_snippets.append(
                        f"{idx}. [{dl['name']}]({dl['url']})\n{_prev_visit(dl['url'])}{dl['snippet'] if 'snippet' in dl else ''}"
                    )

        news_snippets = list()
        if "news" in results:
            for page in results["news"]["value"]:
                idx += 1
                datePublished = ""
                if "datePublished" in page:
                    datePublished = "\nDate published: " + page["datePublished"].split("T")[0]
                news_snippets.append(
                    f"{idx}. [{page['name']}]({page['url']})\n{_prev_visit(page['url'])}{page['description']}{datePublished}"
                )

        video_snippets = list()
        if "videos" in results:
            for page in results["videos"]["value"]:
                if not page["contentUrl"].startswith("https://www.youtube.com/watch?v="):
                    continue
                idx += 1
                datePublished = ""
                if "datePublished" in page:
                    datePublished = "\nDate published: " + page["datePublished"].split("T")[0]
                video_snippets.append(
                    f"{idx}. [{page['name']}]({page['contentUrl']})\n{_prev_visit(page['contentUrl'])}{page['description']}{datePublished}"
                )

        self.page_title = f"{query} - Search"

        content = (
            f"A Bing search for '{query}' found {len(web_snippets) + len(news_snippets) + len(video_snippets)} results:\n\n## Web Results\n"
            + "\n\n".join(web_snippets)
        )
        if len(news_snippets) > 0:
            content += "\n\n## News Results:\n" + "\n\n".join(news_snippets)
        if len(video_snippets) > 0:
            content += "\n\n## Video Results:\n" + "\n\n".join(video_snippets)

        self._set_page_content(content)

    def _fetch_page(self, url: str) -> None:
        download_path = ""
        try:
            if url.startswith("file://"):
                download_path = os.path.normcase(os.path.normpath(url[7:]))
                res = self._mdconvert.convert_local(download_path)
                self.page_title = res.title
                self._set_page_content(res.text_content)
            else:
                # Prepare the request parameters
                request_kwargs = self.request_kwargs.copy() if self.request_kwargs is not None else {}
                request_kwargs["stream"] = True

                # Send a HTTP request to the URL
                response = requests.get(url, **request_kwargs)
                response.raise_for_status()

                # If the HTTP request was successful
                content_type = response.headers.get("content-type", "")

                # Text or HTML
                if "text/" in content_type.lower():
                    res = self._mdconvert.convert_response(response)
                    self.page_title = res.title
                    self._set_page_content(res.text_content)
                # A download
                else:
                    # Try producing a safe filename
                    fname = None
                    download_path = None
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
                    if fname is None:
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
            self.page_title = ("Download complete.",)
            self._set_page_content(f"# Download complete\n\nSaved file to '{download_path}'")
        except FileNotFoundError:
            self.page_title = "Error 404"
            self._set_page_content(f"## Error 404\n\nFile not found: {download_path}")
        except requests.exceptions.RequestException:
            self.page_title = f"Error {response.status_code}"

            # If the error was rendered in HTML we might as well render it
            content_type = response.headers.get("content-type", "")
            if content_type is not None and "text/html" in content_type.lower():
                res = self._mdconvert.convert(response)
                self.page_title = f"Error {response.status_code}"
                self._set_page_content(f"## Error {response.status_code}\n\n{res.text_content}")
            else:
                text = ""
                for chunk in response.iter_content(chunk_size=512, decode_unicode=True):
                    text += chunk
                self.page_title = f"Error {response.status_code}"
                self._set_page_content(f"## Error {response.status_code}\n\n{text}")


# #https://stackoverflow.com/questions/10123929/fetch-a-file-from-a-local-url-with-python-requests
# class LocalFileAdapter(requests.adapters.BaseAdapter):
#     """Protocol Adapter to allow Requests to GET file:// URLs"""
#
#     @staticmethod
#     def _chkpath(method, path):
#         """Return an HTTP status for the given filesystem path."""
#         if method.lower() in ("put", "delete"):
#             return 501, "Not Implemented"
#         elif method.lower() not in ("get", "head"):
#             return 405, "Method Not Allowed"
#         elif not os.path.exists(path):
#             return 404, "File Not Found"
#         elif not os.access(path, os.R_OK):
#             return 403, "Access Denied"
#         else:
#             return 200, "OK"
#
#     def send(self, req, **kwargs):
#         """Return the file specified by the given request"""
#         path = os.path.normcase(os.path.normpath(url2pathname(req.path_url)))
#         response = requests.Response()
#
#         response.status_code, response.reason = self._chkpath(req.method, path)
#         if response.status_code == 200 and req.method.lower() != "head":
#             try:
#                 if os.path.isfile(path):
#                     response.raw = open(path, "rb")
#                 else:  # List the directory
#                     response.headers["content-type"] = "text/html"
#                     pardir = os.path.normpath(os.path.join(path, os.pardir))
#                     pardir_uri = pathlib.Path(pardir).as_uri()
#                     listing = f"""
# <!DOCTYPE html>
# <html>
#   <head>
#     <title>Index of {html.escape(path)}</title>
#   </head>
#   <body>
#     <h1>Index of {html.escape(path)}</h1>
#
#     <a href="{html.escape(pardir_uri, quote=True)}">.. (parent directory)</a>
#
#     <table>
#     <tr>
#        <th>Name</th><th>Size</th><th>Date modified</th>
#     </tr>
# """
#
#                     for entry in os.listdir(path):
#                         full_path = os.path.normpath(os.path.join(path, entry))
#                         full_path_uri = pathlib.Path(full_path).as_uri()
#                         size = ""
#
#                        if os.path.isdir(full_path):
#                            entry = entry + os.path.sep
#                        else:
#                            size = str(os.path.getsize(full_path))
#
#                        listing += (
#                            "<tr>\n"
#                            + f'<td><a href="{html.escape(full_path_uri, quote=True)}">{html.escape(entry)}</a></td>'
#                            + f"<td>{html.escape(size)}</td>"
#                            + f"<td>{html.escape(entry)}</td>"
#                            + "</tr>"
#                        )
#
#                    listing += """
#    </table>
#  </body>
# </html>
# """
#
#                    response.raw = io.StringIO(listing)
#            except (OSError, IOError) as err:
#                response.status_code = 500
#                response.reason = str(err)
#
#        if isinstance(req.url, bytes):
#            response.url = req.url.decode("utf-8")
#        else:
#            response.url = req.url
#
#        response.request = req
#        response.connection = self
#
#        return response
#
#    def close(self):
#        pass
