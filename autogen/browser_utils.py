import json
import os
import requests
import traceback
import re
import markdownify
import io
import uuid
import mimetypes
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional, Union, Tuple

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
IS_SELENIUM_CAPABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.chrome.options import Options as ChromeOptions

    IS_SELENIUM_CAPABLE = True
except ImportError as e:
    print(f"The module/package '{e.name}' is not available.")
    print("Try running 'pip install selenium'.  You may need to run 'sudo easy_install selenium' on Linux or MacOS")
    print("Official selenium installation documentation: https://www.selenium.dev/documentation/webdriver/getting_started/install_library/")
    raise e

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
            self._set_page_content("")
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
        self._set_page_content(content)

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
                    self._set_page_content(re.sub(r"\n{2,}", "\n\n", webpage_text).strip())
                elif content_type == "text/plain":
                    # Get the content of the response
                    plain_text = ""
                    for chunk in response.iter_content(chunk_size=512, decode_unicode=True):
                        plain_text += chunk

                    self.page_title = None
                    self._set_page_content(plain_text)
                elif IS_PDF_CAPABLE and content_type == "application/pdf":
                    pdf_data = io.BytesIO(response.raw.read())
                    self.page_title = None
                    self._set_page_content(pdfminer.high_level.extract_text(pdf_data))
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
                    self._set_page_content(f"Downloaded '{url}' to '{download_path}'.")
                else:
                    self.page_title = f"Error - Unsupported Content-Type '{content_type}'"
                    self._set_page_content(self.page_title)
            else:
                self.page_title = "Error"
                self._set_page_content("Failed to retrieve " + url)
        except requests.exceptions.RequestException as e:
            self.page_title = "Error"
            self._set_page_content(str(e))

get_scheme    = lambda url: urlparse(url).scheme if isinstance(url,str)  else url.scheme
get_domain    = lambda url: urlparse(url).netloc if isinstance(url,str)  else url.netloc
get_path      = lambda url: urlparse(url).path   if isinstance(url, str) else url.path
get_last_path = lambda url: os.path.basename(urlparse(url).path) if isinstance(url, str) else os.path.basename(url.path)

def get_file_path_from_url(url): # URL to Directory function
    """
    get_file_path_from_url function: This function takes a URL as input and returns the corresponding local file path as a string.

    Parameters:
    url (str | ParseResult): The URL of the file for which the local path is to be obtained.

    Returns:
    str: The local file path on the system as a string.
    """

    # Remove any trailing forward slash
    url = url[:-1] if url[-1] == '/' else url

    # Parse the URL
    parsed_url    = urlparse(url) if isinstance(url, str) else url
    canonical_url = parsed_url.netloc.replace("www.","")

    if 'github.com' in url and len(parsed_url.path.split('/')) >= 2:
        relative_path = os.path.join(canonical_url, parsed_url.path)
    elif len(parsed_url.path.split('/')) >= 1:
        relative_path = os.path.join(canonical_url, get_last_path(parsed_url))

    # Remove any preceding forward slash
    relative_path = relative_path[1:] if relative_path[0] == '/' else relative_path
    
    return relative_path

def fix_missing_protocol(img_url, source_url): # Correct a url if it's missing the protocol
    """
    Fixes a URL by adding the missing protocol (http or https) based on the provided domain.

    Parameters:
    - img_url (str): The input image URL to be fixed.
    - domain (str): The domain of the image URL which is used to determine the protocol.

    Returns:
    - str: A corrected URL string with the missing protocol added.
    """

    protocol = get_scheme(source_url)
    domain   = get_domain(source_url) 

    if img_url.startswith('//'):  # If the URL starts with "//"
        img_url = f"{protocol}:{img_url}" # Add "https:" before it
    
    elif not bool(get_domain(img_url)): # domain not in img_url:
        img_url = f"{protocol}://{domain}/{img_url}"
    
    return img_url

def extract_pdf_text(local_pdf_path): # Returns the extracted text content from a local PDF file
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
        text = ''

    return text

def download_using_requests(driver, download_url, save_path): # `requests` downloads assisted by selenium webdriver cookies
    """
    This function takes a Selenium WebDriver instance, a URL to download a file, and a path where you want to save the downloaded file.

    It first retrieves cookies from the given driver, converts them into a format suitable for use with the `requests` library, and then uses these cookies to successfully download the specified file using the `requests.get()` function. The `User-Agent` header is also set to match that used by the WebDriver instance.

    Args:
        driver (webdriver.chrome.webdriver.WebDriver): A Selenium WebDriver instance, typically obtained from selenium.webdriver.Chrome() or another appropriate method for your browser of choice.
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
            cookie_dict[cookie['name']] = cookie['value']
        return cookie_dict

    def download_file_with_cookies(url, session_cookies, save_path, user_agent=None):
        headers = {
            'User-Agent': user_agent if user_agent else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, cookies=session_cookies, headers=headers, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as file:
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

def SeleniumBrowser(**kwargs): # Function that loads the web driver
    """
    This function launches a headless Selenium browser based on the specified 'browser'. The available options are 'edge', 'firefox', and 'chrome'.
    
    Parameters:
        browser (str): A string specifying which browser to launch. Defaults to 'firefox'. 
        download_dir (str): A path to where downloaded files are stored.  Defaults to None

    Returns:
        webdriver: An instance of the Selenium WebDriver based on the specified browser.  User can open a new page by `webdriver.get('https://www.microsoft.com')`.
        
    Raises:
        ImportError: If selenium package is not installed, it raises an ImportError with a message suggesting to install it using pip.
    """    
    
    # Load the argumnets from kwargs
    browser      = kwargs.get('browser', 'edge')
    download_dir = kwargs.get('download_dir', None)

    def get_headless_options(download_dir, options):
        options.headless = True
        options.add_argument('--headless')
        options.add_argument("--window-size=1920,5200")
        options.add_argument('--downloadsEnabled')
        if download_dir:
            options.set_preference("download.default_directory",download_dir)
        return options

    if browser.lower()=='edge':
        driver = webdriver.Edge(options=get_headless_options(download_dir, EdgeOptions()))
    elif browser.lower()=='firefox':
        driver = webdriver.Firefox(options=get_headless_options(download_dir, FirefoxOptions()))
    elif browser.lower()=='chrome':
        driver = webdriver.Chrome(options=get_headless_options(download_dir, ChromeOptions()))
        
    driver.capabilities['se:downloadsEnablead'] = True
    
    return driver 

class SeleniumBrowserWrapper: # A wrapper to bridge compatability between SimpleTextBrowser and SeleniumBrowser
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
        web_driver: Optional[str] = 'edge',
    ):
        self.start_page: str = start_page if start_page else "about:blank"
        self.viewport_size = viewport_size  # Applies only to the standard uri types
        self.downloads_folder = downloads_folder
        self.history: List[str] = list()
        self.page_title: Optional[str] = None
        self.viewport_current_page = 0
        self.viewport_pages: List[Tuple[int, int]] = list()
        self.bing_api_key = bing_api_key
        self.request_kwargs = request_kwargs

        self._page_content = ""

        # Initialize the WebDriver
        self.driver = SeleniumBrowser(browser=web_driver, download_dir=downloads_folder)
        if start_page:
            self.set_address(self.start_page)
            
    @property
    def address(self) -> str:
        """Return the address of the current page."""
        return self.history[-1] if self.history else "about:blank"

    @property
    def viewport(self) -> str:
        """Return the content of the current viewport."""
        return self.driver.page_source  # Selenium directly interacts with the page, no viewport concept

    @property
    def page_content(self) -> str:
        """Return the full contents of the current page."""
        return self.viewport  # In Selenium, viewport essentially contains the full page content

    def set_address(self, uri_or_path: str) -> None:
        """Navigate to a given URI and update history."""
        if not uri_or_path.startswith("http:") and not uri_or_path.startswith("https:"):
            uri_or_path = urljoin(self.address, uri_or_path)
        self.driver.get(uri_or_path)
        self.history.append(uri_or_path)
        self._update_page_content()

    def visit_page(self, path_or_uri: str) -> str:
        """Navigate to a page and return its content."""
        self.set_address(path_or_uri)
        return self.viewport

    def page_down(self) -> None:
        """Simulate page down action."""
        # Simulate pressing Page Down key
        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)

    def page_up(self) -> None:
        """Simulate page up action."""
        # Simulate pressing Page Up key
        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_UP)

    def _update_page_content(self) -> None:
        """Update internal content state, including page title."""
        self.page_title = self.driver.title

    def close(self):
        """Close the browser."""
        self.driver.quit()

    def _split_pages(self) -> None:
        # This is not implemented with the selenium.webdirver wrapper
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
        self._set_page_content(content)

    def download(self, uri_or_path: str) -> None: # TODO: update this based on the new method
        """Download from a given URI"""
        self.driver.get(uri_or_path)

    def _fetch_page(self, url: str) -> None:
        from selenium.common.exceptions import TimeoutException
        try:
            self.driver.get(url)
            self.page_title = self.driver.title
            
            # Selenium WebDriver directly accesses the rendered page, 
            # so we don't need to manually fetch or process the HTML.
            # However, you can still manipulate or extract content from the page using Selenium methods.
            content_type = "text/html"  # Default to text/html since Selenium renders web pages
            
            # Example of extracting and cleaning the page content
            if "wikipedia.org" in url:

                body_elm = self.driver.find_element(By.cssSelector, 'div#mw-content-text')
                main_title = self.driver.title
                webpage_text = "# " + main_title + "\n\n" + markdownify.MarkdownConverter().convert_soup(body_elm.get_attribute('innerHTML'))
            else:
                webpage_text = self.driver.find_element(By.TAG_NAME,'body').get_attribute('innerText')
                        
            # Convert newlines, remove excessive blank lines
            webpage_text = re.sub(r"\r\n", "\n", webpage_text)
            self._set_page_content(re.sub(r"\n{2,}", "\n\n", webpage_text).strip())
            
        except TimeoutException as e:
            self.page_title = "Error"
            self._set_page_content("Timeout while retrieving " + url)

