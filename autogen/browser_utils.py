import json
import os
import requests
import traceback
import re
import markdownify
import io
import uuid
import mimetypes
import hashlib  # Used for generating a content ID from the URL (currently unused)
import random
import string
import tempfile
from math import ceil  # to determine the total number of pages
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from urllib.parse import ParseResult, urljoin, urlparse
from bs4 import BeautifulSoup
from PIL import Image
from IPython.core.display_functions import display

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

# The Selenium package is used to automate web browser interaction from Python
try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException

    # from selenium.webdriver.support.ui import WebDriverWait # We might implement this next
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
    from selenium.webdriver.chrome.options import Options as ChromeOptions

    IS_SELENIUM_CAPABLE = True
except:
    IS_SELENIUM_CAPABLE = False


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
        self.history: List[str] = list()
        self.page_title: Optional[str] = None
        self.viewport_current_page = 0
        self.viewport_pages: List[Tuple[int, int]] = list()
        self.set_address(self.start_page)
        self.bing_api_key = bing_api_key
        self.request_kwargs = request_kwargs

        self._page_content = ""

    @property
    def address(self) -> str:
        """Return the address of the current page."""
        return self.history[-1]

    def set_address(self, uri_or_path: str) -> None:
        self.history.append(uri_or_path)

        # Handle special URIs
        if uri_or_path == "about:blank":
            self.set_page_content("")
        elif uri_or_path.startswith("bing:"):
            self._bing_search(uri_or_path[len("bing:") :].strip())
        else:
            if not uri_or_path.startswith("http:") and not uri_or_path.startswith("https:"):
                uri_or_path = urljoin(self.address, uri_or_path)
                self.history[-1] = uri_or_path  # Update the address with the fully-qualified path
            self._fetch_page(uri_or_path)

        self.viewport_current_page = 0

    @property
    def viewport(self) -> str:
        """Return the content of the current viewport."""
        bounds = self.viewport_pages[self.viewport_current_page]
        return self.page_content[bounds[0] : bounds[1]]

    @property
    def page_content(self) -> str:
        """Return the full contents of the current page."""
        return self._page_content

    def set_page_content(self, content: str) -> None:
        """Sets the text content of the current page."""
        self._page_content = content
        self._split_pages()
        if self.viewport_current_page >= len(self.viewport_pages):
            self.viewport_current_page = len(self.viewport_pages) - 1

    def page_down(self) -> None:
        self.viewport_current_page = min(self.viewport_current_page + 1, len(self.viewport_pages) - 1)

    def page_up(self) -> None:
        self.viewport_current_page = max(self.viewport_current_page - 1, 0)

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

        web_snippets: List[str] = list()
        idx = 0
        for page in results["webPages"]["value"]:
            idx += 1
            web_snippets.append(f"{idx}. [{page['name']}]({page['url']})\n{page['snippet']}")
            if "deepLinks" in page:
                for dl in page["deepLinks"]:
                    idx += 1
                    web_snippets.append(
                        f"{idx}. [{dl['name']}]({dl['url']})\n{dl['snippet'] if 'snippet' in dl else ''}"  # type: ignore[index]
                    )

        news_snippets = list()
        if "news" in results:
            for page in results["news"]["value"]:
                idx += 1
                news_snippets.append(f"{idx}. [{page['name']}]({page['url']})\n{page['description']}")

        self.page_title = f"{query} - Search"

        content = (
            f"A Bing search for '{query}' found {len(web_snippets) + len(news_snippets)} results:\n\n## Web Results\n"
            + "\n\n".join(web_snippets)
        )
        if len(news_snippets) > 0:
            content += "\n\n## News Results:\n" + "\n\n".join(news_snippets)
        self.set_page_content(content)

    def _fetch_page(self, url: str) -> None:
        try:
            # Prepare the request parameters
            request_kwargs = self.request_kwargs.copy() if self.request_kwargs is not None else {}
            request_kwargs["stream"] = True

            # Send a HTTP request to the URL
            response = requests.get(url, **request_kwargs)
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
                    for chunk in response.iter_content(chunk_size=512, decode_unicode=True):
                        html += chunk

                    soup = BeautifulSoup(html, "html.parser")

                    # Remove javascript and style blocks
                    for script in soup(["script", "style"]):
                        script.extract()

                    # Convert to markdown -- Wikipedia gets special attention to get a clean version of the page
                    if url.startswith("https://en.wikipedia.org/"):
                        body_elm = soup.find("div", {"id": "mw-content-text"})
                        title_elm = soup.find("span", {"class": "mw-page-title-main"})

                        if body_elm:
                            # What's the title
                            main_title = soup.title.string
                            if title_elm and len(title_elm) > 0:
                                main_title = title_elm.string
                            webpage_text = (
                                "# " + main_title + "\n\n" + markdownify.MarkdownConverter().convert_soup(body_elm)
                            )
                        else:
                            webpage_text = markdownify.MarkdownConverter().convert_soup(soup)
                    else:
                        webpage_text = markdownify.MarkdownConverter().convert_soup(soup)

                    # Convert newlines
                    webpage_text = re.sub(r"\r\n", "\n", webpage_text)

                    # Remove excessive blank lines
                    self.page_title = soup.title.string
                    self.set_page_content(re.sub(r"\n{2,}", "\n\n", webpage_text).strip())
                elif content_type == "text/plain":
                    # Get the content of the response
                    plain_text = ""
                    for chunk in response.iter_content(chunk_size=512, decode_unicode=True):
                        plain_text += chunk

                    self.page_title = None
                    self.set_page_content(plain_text)
                elif IS_PDF_CAPABLE and content_type == "application/pdf":
                    pdf_data = io.BytesIO(response.raw.read())
                    self.page_title = None
                    self.set_page_content(pdfminer.high_level.extract_text(pdf_data))
                elif self.downloads_folder is not None:
                    # Try producing a safe filename
                    fname = None
                    try:
                        fname = pathvalidate.sanitize_filename(os.path.basename(urlparse(url).path)).strip()
                    except NameError:
                        pass

                    # No suitable name, so make one
                    if fname is None:
                        extension = mimetypes.guess_extension(content_type)
                        if extension is None:
                            extension = ".download"
                        fname = str(uuid.uuid4()) + extension

                    # Open a file for writing
                    download_path = os.path.abspath(os.path.join(self.downloads_folder, fname))
                    with open(download_path, "wb") as fh:
                        for chunk in response.iter_content(chunk_size=512):
                            fh.write(chunk)

                    # Return a page describing what just happened
                    self.page_title = "Download complete."
                    self.set_page_content(f"Downloaded '{url}' to '{download_path}'.")
                else:
                    self.page_title = f"Error - Unsupported Content-Type '{content_type}'"
                    self.set_page_content(self.page_title)
            else:
                self.page_title = "Error"
                self.set_page_content("Failed to retrieve " + url)
        except requests.exceptions.RequestException as e:
            self.page_title = "Error"
            self.set_page_content(str(e))


def get_scheme(url: Union[str, ParseResult]) -> str:
    """
    Extracts the scheme component from a given URL.

    This function supports both string URLs and ParseResult objects. For string URLs, it parses
    the URL and extracts the scheme part. For ParseResult objects, it directly accesses the scheme attribute.

    Args:
        url (Union[str, ParseResult]): The URL from which to extract the scheme. Can be a string or a ParseResult object.

    Returns:
        str: The scheme of the URL (e.g., 'http', 'https').
    """
    return urlparse(url).scheme if isinstance(url, str) else url.scheme


def get_domain(url: Union[str, ParseResult]) -> str:
    """
    Retrieves the domain (network location) component from a URL.

    Similar to `get_scheme`, this function can handle both string representations of URLs and
    ParseResult objects. It extracts the network location part from the URL.

    Args:
        url (Union[str, ParseResult]): The URL from which to extract the domain. Can be a string or a ParseResult object.

    Returns:
        str: The domain of the URL (e.g., 'www.example.com').
    """
    return urlparse(url).netloc if isinstance(url, str) else url.netloc


def get_path(url: Union[str, ParseResult]) -> str:
    """
    Extracts the path component from a URL.

    This function processes both strings and ParseResult objects to return the path segment of the URL.
    The path is the part of the URL that follows the domain but precedes any query parameters or fragment identifiers.

    Args:
        url (Union[str, ParseResult]): The URL from which to extract the path. Can be a string or a ParseResult object.

    Returns:
        str: The path of the URL (e.g., '/path/to/resource').
    """
    return urlparse(url).path if isinstance(url, str) else url.path


def get_last_path(url: Union[str, ParseResult]) -> str:
    """
    Retrieves the last component of the path from a URL.

    This function is useful for extracting the final part of the path, often representing a specific resource or page.
    It handles both string URLs and ParseResult objects. For string URLs, it parses the URL to extract the path and then
    retrieves the last component.

    Args:
        url (Union[str, ParseResult]): The URL from which to extract the last path component. Can be a string or a ParseResult object.

    Returns:
        str: The last component of the path (e.g., 'resource.html').
    """
    return (
        os.path.basename(urlparse(url).path.rstrip("/"))
        if isinstance(url, str)
        else os.path.basename(url.path.rstrip("/"))
    )


def github_path_rule(parsed_url: ParseResult) -> str:
    """Specific rule for GitHub URLs."""
    return os.path.join(parsed_url.netloc.replace("www.", ""), parsed_url.path.lstrip("/"))


def default_path_rule(parsed_url: ParseResult) -> str:
    """Fallback rule for general URLs."""
    return os.path.join(parsed_url.netloc.replace("www.", ""), get_last_path(parsed_url.path))


def get_file_path_from_url(
    url: Union[str, ParseResult],
    domain_rules: Optional[Dict[str, Callable[[ParseResult], str]]] = None,
    default_path_rule: Optional[Callable[[ParseResult], str]] = None,
) -> str:
    """
    Converts a URL into a corresponding local file path, allowing for domain-specific customization.

    This function takes a URL, either as a string or a ParseResult object, and generates a path that represents
    the URL's location in a hypothetical local file system structure. It supports domain-specific rules for
    customizable path generation, with a default rule applied to URLs from domains not explicitly configured.

    Parameters:
        url (Union[str, ParseResult]): The URL to be converted into a local file path.
        domain_rules (Optional[Dict[str, Callable[[ParseResult], str]]]): A dictionary mapping domains to functions
            that define how to construct file paths for URLs from those domains.
        default_path_rule (Optional[Callable[[ParseResult], str]]): A function to construct file paths for URLs
            from domains not covered by `domain_rules`.

    Returns:
        str: The generated local file path, which omits the protocol and optionally adjusts for specific domain structures.
    """
    # Parse the URL if not already
    parsed_url = urlparse(url) if isinstance(url, str) else url
    canonical_url = parsed_url.netloc.replace("www.", "")

    # Determine the appropriate path rule to use
    if domain_rules and canonical_url in domain_rules:
        path_rule = domain_rules[canonical_url]
    else:
        path_rule = (
            default_path_rule
            if default_path_rule
            else lambda u: os.path.join(u.netloc.replace("www.", ""), get_last_path(u.path.rstrip("/")))
        )

    # Generate the relative path using the selected rule
    relative_path = path_rule(parsed_url)

    # Remove any preceding forward slash for consistency
    relative_path = relative_path.lstrip("/")

    return relative_path


def fix_missing_protocol(img_url: str, source_url: str) -> str:
    """
    Ensures that an image URL has a proper protocol specified, using the protocol of a source URL as a reference.

    This function checks if the given image URL lacks a protocol (http or https) and, if so, fixes the URL by
    prepending it with the protocol from the source URL. This is useful for fixing relative URLs or those missing
    a scheme.

    Parameters:
        img_url (str): The image URL to be corrected. It can be a relative URL or one missing a protocol.
        source_url (str): The source URL from which to extract the protocol and, if necessary, the domain.

    Returns:
        str: The corrected image URL with a protocol.

    Note:
        The function handles URLs starting with "//" by directly adding the protocol. If the domain is missing
        from `img_url`, the function constructs the full URL using the protocol and domain from `source_url`.
    """
    protocol = get_scheme(source_url)
    domain = get_domain(source_url)

    if img_url.startswith("//"):  # If the URL starts with "//"
        img_url = f"{protocol}:{img_url}"  # Add "https:" before it

    elif not bool(get_domain(img_url)):  # domain not in img_url:
        img_url = f"{protocol}://{domain}/{img_url}"

    return img_url


def extract_pdf_text(local_pdf_path: str):  # Returns the extracted text content from a local PDF file
    """
    Extracts the text content from a local PDF file and returns it as a string.

    Parameters:
    - local_pdf_path (str): The path to the local PDF file from which the text will be extracted.

    Returns:
    - str: A string containing the text content of the provided PDF file.
    """

    try:
        text = pdfminer.high_level.extract_text(local_pdf_path)
    except Exception:
        traceback.print_exc()
        text = ""

    return text


def download_using_requests(
    driver: Union[
        webdriver.edge.webdriver.WebDriver, webdriver.firefox.webdriver.WebDriver, webdriver.chrome.webdriver.WebDriver
    ],
    download_url: str,
    save_path: str,
) -> None:
    """
    This function takes a Selenium WebDriver instance, a URL to download a file, and a path where you want to save the downloaded file.

    It first retrieves cookies from the given driver, converts them into a format suitable for use with the `requests` library, and then uses these cookies to successfully download the specified file using the `requests.get()` function. The `User-Agent` header is also set to match that used by the WebDriver instance.

    Args:
        driver (webdriver.edge.webdriver.WebDriver): A Selenium WebDriver instance, typically obtained from selenium.webdriver.Edge() or another appropriate method for your browser of choice.
        download_url (str): The URL to the file you want to download.
        save_path (str): The path where you would like the downloaded file to be saved.

    Returns:
        None, but successfully downloads a file from the given URL using the cookies and headers obtained from the WebDriver instance.

    Raises:
        Exception: If the file cannot be downloaded due to an error in the `requests.get()` call.
    """

    def get_cookies(driver):
        return driver.get_cookies()

    def convert_cookies_to_requests_format(cookies):
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie["name"]] = cookie["value"]
        return cookie_dict

    def download_file_with_cookies(url, session_cookies, save_path, user_agent=None):
        headers = {
            "User-Agent": user_agent
            if user_agent
            else "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
        }

        response = requests.get(url, cookies=session_cookies, headers=headers, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)

    # Extract cookies from WebDriver
    cookies = get_cookies(driver)

    # Convert cookies for use with requests
    session_cookies = convert_cookies_to_requests_format(cookies)

    # Define the user-agent if you want to match the one used by your WebDriver
    user_agent = driver.execute_script("return navigator.userAgent;")

    # Download file using requests with the same session cookies and headers
    download_file_with_cookies(download_url, session_cookies, save_path, user_agent=user_agent)


def display_binary_image(binary_data):
    """
    display_binary_image(binary_data):
    This function displays the binary image data in Jupyter notebook cells or shows it in non-notebook environments.

    Args:
    - binary_data (bytes): A bytes object containing the PNG image data.

    Returns:
    - Nothing, but in non-notebook environment, it displays the image.
    """
    img = Image.open(io.BytesIO(binary_data))
    try:
        __IPYTHON__
        display(img)
    except NameError:
        img.show()


def generate_png_filename(url: str):  # Function to help provide a PNG filename (with relative path)
    """
    Generates a PNG filename based on the provided URL, along with a small random hash.

    Args:
        url (str): The URL from which to create a filename.

    Returns:
        str: A unique PNG filename based on the URL and a random hash.
    """

    # Split the URL into its components
    parsed_url = urlparse(url)

    # Generate a 4-character random hash from lowercase letters and digits
    random_hash = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    return f"{'.'.join(parsed_url.netloc.split('.')[-2:])}-{random_hash}.png"


def SeleniumBrowser(**kwargs):  # Function that loads the web driver
    """
    This function launches a headless Selenium browser based on the specified 'browser'. The available options are 'edge', 'firefox', and 'chrome'.

    Parameters:
        browser (str): A string specifying which browser to launch. Defaults to 'firefox'.
        download_dir (str): A path to where downloaded files are stored.  Defaults to None
        resolution (tuple): A tuple of size 2 for screen resolution in the order of width and height.  Defaults to (1920,1080)

    Returns:
        webdriver: An instance of the Selenium WebDriver based on the specified browser.  User can open a new page by `webdriver.get('https://www.microsoft.com')`.
    """

    # Load the arguments from kwargs
    browser = kwargs.get("browser", "edge")
    download_dir = kwargs.get("download_dir", tempfile.gettempdir())
    if not download_dir:
        download_dir = tempfile.gettempdir()

    browser_res = kwargs.get("resolution", (1920, 1080))

    def get_headless_options(download_dir, options):
        options.headless = True
        options.add_argument("--headless")
        options.add_argument(f"--window-size={browser_res[0]},{browser_res[1]}")
        options.add_argument("--downloadsEnabled")
        if download_dir:
            options.set_preference("download.default_directory", download_dir)
        return options

    if browser.lower() == "edge":
        options = EdgeOptions()
        options.use_chromium = True  # Ensure we're using the Chromium-based version of Edge
        options.headless = True
        options.add_argument("--headless")
        options.add_argument(f"--window-size={browser_res[0]},{browser_res[1]}")
        options.add_argument("--downloadsEnabled")

        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,  # Disable download prompt
            "download.directory_upgrade": True,  # Enable directory upgrade
            "safebrowsing.enabled": True,  # Enable safe browsing
        }
        options.add_experimental_option("prefs", prefs)
        # Instantiate the EdgeService object
        edge_service = EdgeService()
        # Instantiate the Edge WebDriver with the configured options
        driver = webdriver.Edge(options=options, service=edge_service)

    elif browser.lower() == "firefox":
        # Instantiate the Firefox Profile to specify options
        profile = FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)  # Custom location
        profile.set_preference("browser.download.dir", download_dir)
        profile.set_preference("browser.download.useDownloadDir", True)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")  # MIME type
        profile.set_preference("javascript.enabled", False)
        profile.update_preferences()
        options = FirefoxOptions()
        options.profile = profile
        options.set_capability("se:downloadsEnabled", True)

        # Instantiate the Firefox WebDriver with the configured options
        driver = webdriver.Firefox(options=get_headless_options(download_dir, options))

    elif browser.lower() == "chrome":
        # Instantiate the Chrome Options
        options = ChromeOptions()
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,  # Disable download prompt
            "download.directory_upgrade": True,  # Enable directory upgrade
            "safebrowsing.enabled": True,  # Enable safe browsing
        }
        options.add_experimental_option("prefs", prefs)
        # Instantiate the Chrome WebDriver with the configured options
        driver = webdriver.Chrome(options=get_headless_options(download_dir, options))

    else:
        raise (f"Unknown browser type {browser}")

    # Ensure that downloads are permitted
    driver.capabilities["se:downloadsEnablead"] = True
    # Ensure that the window is at the expected size
    driver.set_window_size(browser_res[0], browser_res[1])

    return driver


class SeleniumBrowserWrapper:  # A wrapper to bridge compatibility between SimpleTextBrowser and SeleniumBrowser
    """
    SeleniumBrowserWrapper class is a wrapper that manages the interaction with a Selenium web driver.
    It provides methods to control the browser, set up the viewport size, and download files.

    Parameters:
    - start_page (Optional[str]): The initial URL of the web page to load. Defaults to "about:blank".
    - viewport_size (Optional[int]): The width of the viewport in pixels. Defaults to 1024 * 8.
    - downloads_folder (Optional[Union[str, None]]): The directory where downloaded files will be saved. If set to `None`, default downloads folder will be used.
    - bing_api_key (Optional[Union[str, None]]): The API key for Bing search engine.
    - request_kwargs (Optional[Union[Dict[str, Any], None]]): Additional keyword arguments that can be passed for customization.
    - web_driver (Optional[str]): The type of web driver to use. Defaults to 'edge'.

    Attributes:
    - start_page (str): The initial URL of the web page to load.
    - viewport_size (int): The width of the viewport in pixels.
    - downloads_folder (Union[str, None]): The directory where downloaded files will be saved.
    - history (List[str]): A list containing the URLs visited by the browser.
    - page_title (Optional[str]): The title of the current web page.
    - viewport_current_page (int): The index of the current web page in relation to all pages loaded.
    - viewport_pages (List[Tuple[int, int]]): A list containing tuples of width and height for each viewed web page.
    - bing_api_key (Optional[str]): The API key for Bing search engine.
    - request_kwargs (Optional[Union[Dict[str, Any], None]]): Additional keyword arguments passed during instantiation.
    - _page_content (str): The content of the current web page.
    - driver: An instance of SeleniumBrowser class that manages the browser interaction.

    Notes:
    - Viewport Size and Pages: The concept of viewport size and pagination doesn't directly apply to Selenium as it does in a text-based browser. Selenium interacts with the whole page. However, actions like scrolling can be simulated.
    - Downloads Folder: This is handled through ChromeOptions if you need to set a default download directory.
    - History Management: This wrapper maintains a simple history of visited URLs for compatibility with the SimpleTextBrowser's API.
    - Page Content: Selenium's page_source property provides the HTML content of the current page, making the distinction between viewport and page content less relevant.

    """

    def __init__(
        self,
        start_page: Optional[str] = None,
        viewport_size: Optional[int] = 1024 * 8,
        downloads_folder: Optional[Union[str, None]] = None,
        bing_api_key: Optional[Union[str, None]] = None,
        request_kwargs: Optional[Union[Dict[str, Any], None]] = None,
        browser: Optional[str] = "edge",
        page_load_time: Optional[int] = 6,
        resolution: Optional[Tuple] = (1920, 1080),
        render_text: Optional[bool] = False,
    ):
        self.start_page: str = start_page if start_page else "about:blank"
        self.downloads_folder = downloads_folder
        self.history: List[str] = list()
        self.page_title: Optional[str] = None
        self.viewport_current_page = 0
        self.viewport_pages: List[Tuple[int, int]] = list()
        self.bing_api_key = bing_api_key
        self.request_kwargs = request_kwargs
        self.page_load_time = page_load_time
        self._page_content = ""
        self.window_width = resolution[0]
        self.window_height = resolution[1]
        self.viewport_size = resolution[1]  # We override this from SimpleTextBrowser to match the browser window height
        self.render_text = render_text  # Just in case for functionality purposes

        # Initialize the WebDriver
        self.driver = SeleniumBrowser(browser=browser, download_dir=downloads_folder, resolution=resolution)
        if start_page:
            self.set_address(self.start_page)

    @property
    def address(self) -> str:
        """Return the address of the current page."""
        return self.history[-1] if self.history else "about:blank"

    @property
    def viewport(self) -> str:
        """Return the content of the current viewport."""
        return self._page_content

    @property
    def page_content(self) -> str:
        """Return the full contents of the current page."""
        return self.viewport  # In Selenium, viewport essentially contains the full page content

    def set_address(self, uri_or_path: str) -> None:
        """Navigate to a given URI and update history."""
        if not uri_or_path.startswith("http:") and not uri_or_path.startswith("https:"):
            uri_or_path = urljoin(self.address, uri_or_path)

        self.history.append(uri_or_path)

        # Handle special URIs
        if uri_or_path == "about:blank":
            self.set_page_content("")
        elif uri_or_path.startswith("bing:"):
            self._bing_search(uri_or_path[len("bing:") :].strip())
        else:
            if not uri_or_path.startswith("http:") and not uri_or_path.startswith("https:"):
                uri_or_path = urljoin(self.address, uri_or_path)
                self.history[-1] = uri_or_path  # Update the address with the fully-qualified path
            # Navigate to the specified URI or path
            self._fetch_page(uri_or_path)

        self.viewport_current_page = 0
        self._split_pages()

    def visit_page(self, path_or_uri: str) -> str:
        """Navigate to a page and return its content."""
        self.set_address(path_or_uri)
        return self.viewport

    def page_down(self) -> None:
        """Simulate page down action."""
        # Simulate pressing Page Down key
        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)

    def page_up(self) -> None:
        """Simulate page up action."""
        # Simulate pressing Page Up key
        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_UP)

    def _update_page_content(self) -> None:
        """Update internal content state, including page title."""
        self.page_title = self.driver.title

    def close(self):
        """Close the browser."""
        self.driver.quit()

    def _split_pages(self) -> None:
        # Page scroll position
        int(self.driver.execute_script("return document.documentElement.scrollHeight"))

        # Grab the current page height based on the scrollbar
        self.page_height = self.driver.execute_script("return window.pageYOffset + window.innerHeight")

        # Calculate the total number of pages currently rendered
        self.page_count = ceil(self.window_height / self.page_height)

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
        while start_idx < self.page_height:
            end_idx = min(start_idx + self.viewport_size, self.page_height)  # type: ignore[operator]
            self.viewport_pages.append((start_idx, end_idx))
            start_idx = end_idx

        return

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
        self.bing_results = results
        web_snippets: List[str] = list()
        idx = 0
        for page in results["webPages"]["value"]:
            idx += 1
            web_snippets.append(f"{idx}. [{page['name']}]({page['url']})\n{page['snippet']}")
            if "deepLinks" in page:
                for dl in page["deepLinks"]:
                    idx += 1
                    web_snippets.append(
                        f"{idx}. [{dl['name']}]({dl['url']})\n{dl['snippet'] if 'snippet' in dl else ''}"  # type: ignore[index]
                    )

        news_snippets = list()
        if "news" in results:
            for page in results["news"]["value"]:
                idx += 1
                news_snippets.append(f"{idx}. [{page['name']}]({page['url']})\n{page['description']}")

        self.page_title = f"{query} - Search"

        content = (
            f"A Bing search for '{query}' found {len(web_snippets) + len(news_snippets)} results:\n\n## Web Results\n"
            + "\n\n".join(web_snippets)
        )
        if len(news_snippets) > 0:
            content += "\n\n## News Results:\n" + "\n\n".join(news_snippets)

        self.set_page_content(content)

    def set_page_content(self, content):
        """Sets the text content of the current page."""
        self._page_content = content

        # Your custom HTML content
        custom_html_content = "<html><body>" + content.replace("\n", "<br>") + "</body></html>"

        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html") as tmp_file:
            tmp_file.write(custom_html_content)
            html_file_path = tmp_file.name

        # Navigate to the file
        self.driver.get(f"file://{html_file_path}")

    def download(self, uri_or_path: str) -> None:
        """Download from a given URI"""
        download_using_requests(self.driver, self.downloads_folder, os.path.basename(uri_or_path.rstrip("/")))

    def _get_headers(self):
        def parse_list_to_dict(lst):
            result_dict = {}
            for item in lst:
                key, value = item.split(": ", 1)
                # Attempt to load JSON content if present
                try:
                    value_json = json.loads(value)
                    result_dict[key] = value_json
                except json.JSONDecodeError:
                    # Handle non-JSON value
                    result_dict[key] = value
            return result_dict

        headers = self.driver.execute_script(
            "var req = new XMLHttpRequest();req.open('GET', document.location, false);req.send(null);return req.getAllResponseHeaders()"
        )
        headers = headers.splitlines()
        headers = parse_list_to_dict(headers)
        return headers

    def _fetch_page(self, url: str) -> None:
        try:
            self.driver.get(url)
            self.driver.implicitly_wait(self.page_load_time)
            self.history.append(url)
            headers = self._get_headers()

            self.page_title = self.driver.title

            # We can't get response codes without using a proxy or using requests in a double call
            content_type = headers.get("content-type", "")
            for ct in ["text/html", "text/plain", "application/pdf"]:
                if ct in content_type.lower():
                    content_type = ct
                    break

            if content_type == "text/html":
                html = self.driver.page_source
                soup = BeautifulSoup(html, "html.parser")

                # Remove javascript and style blocks
                for script in soup(["script", "style"]):
                    script.extract()

                # Convert to markdown -- Wikipedia gets special attention to get a clean version of the page
                if url.startswith("https://en.wikipedia.org/"):
                    body_elm = soup.find("div", {"id": "mw-content-text"})
                    title_elm = soup.find("span", {"class": "mw-page-title-main"})

                    if body_elm:
                        # What's the title
                        main_title = soup.title.string
                        if title_elm and len(title_elm) > 0:
                            main_title = title_elm.string
                        webpage_text = (
                            "# " + main_title + "\n\n" + markdownify.MarkdownConverter().convert_soup(body_elm)
                        )
                    else:
                        webpage_text = markdownify.MarkdownConverter().convert_soup(soup)
                else:
                    webpage_text = markdownify.MarkdownConverter().convert_soup(soup)

                # Convert newlines
                webpage_text = re.sub(r"\r\n", "\n", webpage_text)

                # Remove excessive blank lines
                if self.render_text:
                    self.page_title = soup.title.string
                    self.set_page_content(webpage_text.strip())
                else:
                    self._page_content = webpage_text

            elif content_type == "text/plain":
                html = self.driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                plain_text = soup.prettify()
                if self.render_text:
                    self.page_title = None
                    self.set_page_content(plain_text)
                else:
                    self._page_content = plain_text

            elif IS_PDF_CAPABLE and content_type == "application/pdf":
                download_using_requests(self.driver, self.downloads_folder, os.path.basename(url))
                plain_text = extract_pdf_text(os.path.join(self.downloads_folder, os.path.basename(url)))
                if self.render_text:
                    self.page_title = None
                    self.set_page_content(plain_text)
                else:
                    self._page_content = plain_text

            elif self.downloads_folder is not None:
                # Try producing a safe filename
                fname = None
                try:
                    fname = pathvalidate.sanitize_filename(os.path.basename(urlparse(url).path)).strip()
                except NameError:
                    pass

                # No suitable name, so make one
                if fname is None:
                    extension = mimetypes.guess_extension(content_type)
                    if extension is None:
                        extension = ".download"
                    fname = str(uuid.uuid4()) + extension

                # Open a file for writing
                download_path = os.path.abspath(os.path.join(self.downloads_folder, fname))
                download_using_requests(self.driver, self.downloads_folder, fname)

                # Return a page describing what just happened
                if self.render_text:
                    self.page_title = "Download complete."
                    self.set_page_content(f"Downloaded '{url}' to '{download_path}'.")
                else:
                    self._page_content = f"Downloaded '{url}' to '{download_path}'."

            elif self.render_text:
                self.page_title = f"Error - Unsupported Content-Type '{content_type}'"
                self.set_page_content(self.page_title)
            else:
                self._page_content = None

        except requests.exceptions.RequestException as e:
            self.page_title = "Error"
            self.set_page_content(str(e))
