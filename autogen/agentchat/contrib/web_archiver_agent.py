from ..agent import Agent
from ..conversable_agent import ConversableAgent
from ..assistant_agent import AssistantAgent
from ...browser_utils import (
    SeleniumBrowser,
    download_using_requests,
    get_domain,
    get_scheme,
    get_path,
    get_last_path,
    github_path_rule,
    get_file_path_from_url,
    fix_missing_protocol,
    extract_pdf_text,
)
from typing import List, Union, Any, Tuple, Dict
import os
import re
import json
import traceback
import requests
from collections import deque
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
import base64

# Import the arxiv library if it is available
IS_ARXIV_CAPABLE = False
try:
    import arxiv

    IS_ARXIV_CAPABLE = True
except ModuleNotFoundError:
    print("The 'arxiv' library was not found in this environment, but can be installed with 'pip install arxiv'.")
    pass


class WebArchiverAgent(ConversableAgent):
    def __init__(
        self,
        silent: bool = True,
        storage_path: str = "./content",
        max_depth: int = 1,
        page_load_time: float = 6,
        *args,
        **kwargs,
    ):
        """
        WebArchiverAgent: Custom LLM agent for collecting online content.

        The WebArchiverAgent class is a custom Autogen agent that can be used to collect and store online content from different
        web pages. It extends the ConversableAgent class and provides additional functionality for managing a list of
        additional links, storing collected content in local directories, and customizing request headers.  WebArchiverAgent
        uses deque to manage a list of additional links for further exploration, with a maximum depth limit set by max_depth
        parameter. The collected content is stored in the specified storage path (storage_path) using local directories.
        WebArchiverAgent can be customized with request_kwargs and llm_config parameters during instantiation. The default
        User-Agent header is used for requests, but it can be overridden by providing a new dictionary of headers under
        request_kwargs.

        Parameters:
            silent (bool): If True, the agent operates in silent mode with minimal output. Defaults to True.
            storage_path (str): The path where the collected content will be stored. Defaults to './content'.
            max_depth (int): Maximum depth limit for exploring additional links from a web page. This defines how deep
                            the agent will go into linked pages from the starting point. Defaults to 1.
            page_load_time (float): Time in seconds to wait for loading each web page. This ensures that dynamic content
                                    has time to load before the page is processed. Defaults to 6 seconds.
            *args, **kwargs: Additional arguments and keyword arguments to be passed to the parent class `ConversableAgent`.
                            These can be used to configure underlying behaviors of the agent that are not explicitly
                            covered by the constructor's parameters.

        Note:
            The `silent` parameter can be useful for controlling the verbosity of the agent's operations, particularly
            in environments where logging or output needs to be minimized for performance or clarity.

        Software Dependencies:
            - requests
            - beautifulsoup4
            - pdfminer
            - selenium
            - arxiv
            - pillow
        """

        self.browser_kwargs = kwargs.pop("browser_config", {"browser": "firefox"})
        super().__init__(*args, **kwargs)

        self.additional_links = deque()
        self.link_depth = 0
        self.max_depth = max_depth
        self.local_dir = storage_path
        self.page_load_time = page_load_time
        self.silent = silent
        self.request_kwargs = {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
            }
        }
        self.small_llm_config = kwargs["llm_config"]
        self.process_history = {}
        self.browser = None
        self.domain_path_rules = {
            "github.com": github_path_rule,
            # Add more domain rules as needed
        }

        # Define the classifiers
        self._define_classifiers()

    def classifier_to_collector_reply(
        self,
        recipient: Agent,
        messages: Union[List[str], str],
        sender: Agent,
        config: dict,
    ) -> Tuple[bool, str]:
        """
        Processes the last message in a conversation to generate a boolean classification response.

        This method takes the most recent message from a conversation, uses the recipient's method to generate a reply,
        and classifies the reply as either "True" or "False" based on its content. It is designed for scenarios where
        the reply is expected to represent a boolean value, simplifying downstream processing.

        Parameters:
            recipient (Agent): The agent or object responsible for generating replies. Must have a method `generate_oai_reply`
                               that accepts a list of messages, a sender, and optionally a configuration, and returns a tuple
                               where the second element is the reply string.
            messages (Union[List[str], str]): A list of messages or a single message string from the conversation. The last message
                                              in this list is used to generate the reply.
            sender (Agent): The entity that sent the message. This could be an identifier, an object, or any representation
                            that the recipient's reply generation method expects.
            config (dict): Configuration parameters for the reply generation process, if required by the recipient's method.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean status (always True in this implementation) and the classification result
                            as "True" or "False" based on the content of the generated reply.

        Note:
            The classification is case-insensitive and defaults to "False" if the reply does not explicitly contain
            "true" or "false". This behavior ensures a conservative approach to classification.
        """
        last_message = messages[-1] if isinstance(messages, list) else messages
        _, rep = recipient.generate_oai_reply([last_message], sender)

        # Streamlined classification logic
        rep_lower = rep.lower()
        classified_reply = "True" if "true" in rep_lower else "False"

        return True, classified_reply

    def _define_classifiers(self):
        """
        Defines the agents used for classification tasks.

        Parameters:
        - None

        Returns:
        - None
        """
        # Define the system messages for the classifiers
        self.metadata_classifier_system_msg = "Help the user identify if the metadata contains potentially useful information such as: author, title, description, a date, etc. Respond True for useful, False for not."
        self.content_classifier_system_msg = "You are to classify web data as content or other (such as an adversitement) based on the page title.  Respond True if it is content, False if not."

        # Define the prompt templates for the classifiers
        self.content_classifier_prompt = lambda title, content: f"Title: `{title}`, Data: ```{content}`"
        self.metadata_classifier_prompt = (
            lambda content: f"We are parsing html metadata to extract useful data. Should we hold onto this item? {content}."
        )

        # Define the metadata classifier
        self.metadata_classifier = AssistantAgent(
            "Metadata Classifier",
            system_message=self.metadata_classifier_system_msg,
            llm_config=self.small_llm_config,
            max_consecutive_auto_reply=0,
        )
        self.metadata_classifier.register_reply(self, self.classifier_to_collector_reply, 1)

        # Define the html content classifier
        self.content_classifier = AssistantAgent(
            "Content Classifier",
            system_message=self.content_classifier_system_msg,
            llm_config=self.small_llm_config,
            max_consecutive_auto_reply=0,
        )
        self.content_classifier.register_reply(self, self.classifier_to_collector_reply, 1)

    def _fetch_content(self, link: str) -> Tuple[str, str]:
        """
        Fetches content from a given URL.

        Parameters:
        - link (str): The URL from which to fetch content.

        Returns:
        - Tuple[str, str]: Content type and fetched content or error message.
        """
        # Parse the link
        parsed_url = urlparse(link)

        # A special case for arxiv links
        if "arxiv" in link and IS_ARXIV_CAPABLE:
            return "pdf", self._fetch_arxiv_content(parsed_url)

        elif parsed_url.path.endswith(".pdf"):
            return "pdf", self._fetch_pdf_content(link)

        else:
            return "html", self._fetch_html_content(link)

    def _fetch_html_content(self, link: str) -> str:
        """
        Handles the fetching of HTML content from a web page.

        Parameters:
        - link (str): The URL of the web page.

        Returns:
        - str: Success (errors are handled at the higher level)
        """
        # Handle web page content (html)

        sd = {}  # submission_data
        sd["url"] = link

        # Establish the downloads folder
        sd["local_path"] = os.path.join(self.local_dir, get_file_path_from_url(link, self.domain_path_rules))
        os.makedirs(sd["local_path"], exist_ok=True)

        # We can instantiate the browser now that we know where the files and downloads will go
        self.browser = SeleniumBrowser(browser=self.browser_kwargs["browser"], download_dir=sd["local_path"])

        if "github.com" in link and "README.md" not in link:
            # Small patch to facilitate github repos
            link = os.path.join(link, "README.md")

        self.browser.get(link)
        self.browser.maximize_window()
        self.browser.implicitly_wait(self.page_load_time)

        # Define where the screeshot is stored
        sd["browser_screenshot_path"] = os.path.join(sd["local_path"], "screenshot.png")

        # Save a screenshot of the browser window
        if self.browser_kwargs["browser"] == "firefox":
            # save_full_page_screenshot
            self.browser.save_full_page_screenshot(sd["browser_screenshot_path"])
        else:
            page_height = self.browser.execute_script("return window.pageYOffset + window.innerHeight")
            self.browser.set_window_size(1920, page_height)
            self.browser.save_screenshot(sd["browser_screenshot_path"])

        sd["title"] = self.browser.title
        sd["html"] = self.browser.page_source

        # Write the HTML to disk for archival purposes
        with open(os.path.join(sd["local_path"], "index.html"), "w", encoding="utf-8") as f:
            f.write(str(self.browser.page_source))

        # Store the BS object
        sd["soup"] = BeautifulSoup(sd["html"], "html.parser")

        sd["content"] = self._identify_content(sd["soup"])

        # Save the content to a text file on disk
        with open(os.path.join(sd["local_path"], "content.txt"), "w") as f:
            for data in sd["content"]:  # Iterate over each record
                f.write(data + "\n")  # Write the content to the file

        # Save the original URL for convenience elsewhere (when parsing images)
        sd["soup"].url = link

        # Parse and store the Metadata
        sd["meta"] = self._identify_metadata(sd["soup"])  # [ data.attrs for data in sd['soup'].find_all("meta") ]

        # Open a file to write the metadata to
        with open(os.path.join(sd["local_path"], "metadata.txt"), "w") as f:
            for data in sd["meta"]:  # Iterate over each record
                f.write(json.dumps(data) + "\n")  # Write the link to the file

        # Parse and store the links
        sd["links"] = [
            {"text": link.get_text().strip(), "href": link["href"]}
            for link in sd["soup"].find_all("a")
            if link.has_attr("href") and "/" in link["href"]
        ]

        # Open a file to write the link URLs to
        with open(os.path.join(sd["local_path"], "links.txt"), "w") as f:
            for link in sd["links"]:  # Iterate over each link
                f.write(json.dumps(link) + "\n")  # Write the link to the file

                # Recursive link checking, up to 1 level deep past the root
                if self.link_depth < 1:
                    # Check if we find any useful relevant links that we should catalog
                    if (
                        "project" in link["text"] or "paper" in link["text"] or "code" in link["text"]
                    ) and "marktekpost" in link["href"].lower():
                        self.additional_links.append(link["href"])
                    elif "arxiv" in link["href"] or (
                        "github.com" in link["href"]
                        and (link["href"][:-3] != ".md" or os.path.basename(link["href"]) == "README.md")
                    ):
                        self.additional_links.append(link["href"])

        # Parse and store the images
        self._collect_images(sd["soup"], sd["local_path"])

        # Close down the browser
        self.browser.quit()

        # Log the processed link, motivated by the unit test
        self.process_history[sd["url"]] = sd

        return "success"

    def _fetch_pdf_content(self, link: str) -> str:
        """
        Fetches PDF content from a given URL.

        Parameters:
        - link (str): The URL from which to fetch the PDF content.

        Returns:
        - str: Extracted content or None in a failure event
        """
        local_pdf_path = os.path.join(
            self.local_dir, os.path.join(get_file_path_from_url(link, self.domain_path_rules), link.split("/")[-1])
        )
        os.makedirs(local_pdf_path, exist_ok=True)

        # This could be replaced with `download_using_requests`
        response = requests.get(link, params={"headers": self.request_kwargs["headers"]})

        if response.status_code == 200:
            with open(local_pdf_path, "wb") as f:
                f.write(response.content)

            # Extract text from the PDF file
            text = extract_pdf_text(local_pdf_path)

            # Let's store the content to disk for later access
            with open(local_pdf_path.replace("pdf", "txt"), "w") as f:
                f.write(text)

            return text
        else:
            return None

    def _fetch_arxiv_content(self, link: str) -> str:
        """
        Fetches content specifically from arXiv URLs.

        Parameters:
        - link (str): The arXiv URL from which to fetch content.

        Returns:
        - str: Extracted text content
        """
        # Identify the paper identification
        arxiv_id = link.path.split("/")[-1]

        # Define the local directory
        local_base_path = os.path.join(self.local_dir, get_file_path_from_url(link, self.domain_path_rules))
        os.makedirs(local_base_path, exist_ok=True)

        local_pdf_path = os.path.join(local_base_path, f"{arxiv_id}.pdf")

        # Download the paper if we don't already have it
        if not os.path.exists(local_pdf_path):
            # Define the record belonging to the paper
            paper = next(arxiv.Client().results(arxiv.Search(id_list=[arxiv_id])))

            # Download the archive to the local downloads folder.
            paper.download_pdf(dirpath=local_base_path, filename=f"{arxiv_id}.pdf")

            # Download the archive to the local downloads folder.
            paper.download_source(dirpath=local_base_path, filename=f"{arxiv_id}.tar.gz")

        text = extract_pdf_text(local_pdf_path)

        # Let's store the content to disk for later access
        with open(local_pdf_path.replace("pdf", "txt"), "w") as f:
            f.write(text)

        return text

    def _identify_content(self, soup: BeautifulSoup) -> List[str]:
        """
        Identifies the title of the web page from the BeautifulSoup object.

        Parameters:
        - soup (BeautifulSoup): BeautifulSoup object of the web page.

        Returns:
        - list: A list of all text content classified as relevant
        """
        # Get the page title for use with the queries
        page_title = soup.find("head").find("title").string

        # Find and extract relevant content from soup based on the title
        relevant_content = []

        for element in soup.find_all(True):
            if element.name in ["h1", "h2", "h3", "p"]:
                text = element.text.strip().replace("\t", " ").replace("\n", " ")
                if len(text) > 0:
                    while text.find("  ") != -1:
                        text = text.replace("  ", " ")
                    prompt = self.content_classifier_prompt(page_title, text)
                    relevant = self.initiate_chat(
                        self.content_classifier, message=prompt, max_turns=1, max_tokens=8, silent=self.silent
                    ).chat_history[-1]["content"]
                    if relevant == "True":
                        relevant_content.append(text.strip())
                        if not self.silent:
                            print(element)

        return relevant_content

    def _identify_metadata(self, soup: BeautifulSoup, verbose: bool = False) -> List[Dict]:
        """
        Extracts metadata from the web page using BeautifulSoup.

        Parameters:
        - soup (BeautifulSoup): BeautifulSoup object of the web page.
        - verbose (bool): Flag to enable verbose logging.

        Returns:
        - List[Dict]: A list of dictionaries representing the relevant Metadata extracted from the page.
        """
        soup.find("head").find("title").string
        relevant_content = []
        for data in soup.find_all("meta"):
            relevant = False

            prompt = self.metadata_classifier_prompt(data.attrs)

            if "content" in data.attrs and "http" in data.attrs["content"]:
                relevant = True
            elif "content" in data.attrs:
                data.attrs["content"] = data.attrs["content"].strip()
                relevant = self.initiate_chat(
                    self.metadata_classifier, message=prompt, max_turns=1, max_tokens=8, silent=self.silent
                ).chat_history[-1]["content"]
            elif "property" in data.attrs:
                data.attrs["property"] = data.attrs["property"].strip()
                relevant = self.initiate_chat(
                    self.metadata_classifier, message=prompt, max_turns=1, max_tokens=8, silent=self.silent
                ).chat_history[-1]["content"]
            elif "name" in data.attrs:
                data.attrs["name"] = data.attrs["name"].strip()
                relevant = self.initiate_chat(
                    self.metadata_classifier, message=prompt, max_turns=1, max_tokens=8, silent=self.silent
                ).chat_history[-1]["content"]

            if relevant == "True":
                relevant_content.append(data.attrs)
                if verbose:
                    print(data.attrs)

        return relevant_content

    def _collect_images(self, soup: BeautifulSoup, local_path: str, verbose: bool = False) -> None:
        """
        Collects and saves images from the web page to a local path.

        Parameters:
        - soup (BeautifulSoup): BeautifulSoup object of the web page.
        - local_path (str): The local directory path where images will be saved.
        - verbose (bool): Flag to enable verbose logging.

        Returns:
        - None
        """

        def get_basename(filename):
            return os.path.splitext(os.path.basename(filename))[0]

        for img in soup.find_all("img"):
            img_alt = img.attrs["alt"] if "alt" in img.attrs else ""
            img_src = img.attrs["src"].lower()

            if "png;base64" in img_src:
                # Step 1: Strip the prefix to get the Base64 data
                encoded_data = img.attrs["src"].split(",")[1]

                # Step 2: Decode the Base64 string
                image_data = base64.b64decode(encoded_data)

                # Step 3: Create a BytesIO buffer from the decoded data
                image_buffer = BytesIO(image_data)

                # Step 4: Open the image using PIL
                image = Image.open(image_buffer)

                # Save the image to a file
                image.save(f"{img_src.replace('data:image/png;base64','')[:28]}.png")

            elif "logo" in img_src:
                continue

            elif (
                "png" in img_src
                or "jpg" in img_src
                or "jpeg" in img_src
                or "webp" in img_src
                or "avif" in img_src
                or "heif" in img_src
                or "heic" in img_src
                or "svg" in img_src
            ):
                file_name = img_src.split("/")[-1]  # there are other ways to do this
                local_image_description_path = os.path.join(local_path, get_basename(file_name) + ".txt")
                local_image_path = os.path.join(local_path, file_name)
                if len(img_alt) > 0 and not os.path.exists(local_image_description_path):
                    with open(local_image_description_path, "w") as f:
                        f.write(img_alt)
                if not os.path.exists(local_image_path):
                    image_url = fix_missing_protocol(img.attrs["src"], soup.url)
                    try:
                        # response = requests.get(image_url, params={'headers': self.request_kwargs})
                        download_using_requests(self.browser, image_url, local_image_path)
                    except Exception:
                        print(image_url, img.attrs["src"])
                        traceback.print_exc()

    # Main entry point
    def collect_content(
        self,
        recipient: Agent,
        messages: Union[List[str], str],
        sender: Agent,
        config: dict,
    ) -> Tuple[bool, str]:
        """
        Collects and archives content from links found in messages.

        This function scans messages for URLs, fetches content from these URLs,
        and archives them to a specified local directory. It supports recursive
        link fetching up to a defined depth.

        Parameters:
        - recipient (Agent): The agent designated to receive the content.
        - messages (Union[List[str], str]): A list of messages or a single message containing URLs.
        - sender (Agent): The agent sending the content.
        - config (dict): Configuration parameters for content fetching and archiving.

        Returns:
        - Tuple[bool, str]: A tuple where the first element is a boolean indicating
          success or failure, and the second element is a string message detailing
          the outcome or providing error logs in case of failure.
        """

        try:
            content_type, content = "", ""
            all_links = []
            for message in messages:
                if message.get("role") == "user":
                    links = re.findall(
                        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                        message.get("content"),
                    )
                    for link in links:
                        all_links.append(link)

            # Process the links provided by the user
            for link in all_links:
                content_type, content = self._fetch_content(link)

            # Inform self that it has completed the root level of link(s)
            self.link_depth = 1
            if self.link_depth <= self.max_depth:
                while len(self.additional_links) > 0:
                    additional_link = self.additional_links.pop()
                    content_type, content = self._fetch_content(additional_link)
                    all_links.append(all_links)

            self.link_depth = 0
            return (
                True,
                f"Success: archived the following links in your chosen location {self.local_dir}/ <-- {', '.join(all_links)}",
            )
        except Exception:
            # Return traceback information in case of an exception
            error_log = traceback.format_exc()
            return False, f"Failed to collect content due to an error: {error_log}"
