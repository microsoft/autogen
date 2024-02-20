from ..conversable_agent import ConversableAgent
from ..assistant_agent import AssistantAgent
from ...browser_utils import (
    SeleniumBrowser,
    download_using_requests,
    get_domain,
    get_scheme,
    get_path,
    get_last_path,
    get_file_path_from_url,
    fix_missing_protocol,
    extract_pdf_text,
)

import os
import re
import json
import traceback
import requests
from collections import deque
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup

# Import the arxiv library if it is available
IS_ARXIV_CAPABLE = False
try:
    import arxiv

    IS_ARXIV_CAPABLE = True
except ModuleNotFoundError:
    print("The 'arxiv' library was not found in this environment, but can be installed with 'pip install arxiv'.")
    pass


class ContentAgent(ConversableAgent):
    """
    ContentAgent: Custom LLM agent for collecting online content.

    The ContentAgent class is a custom Autogen agent that can be used to collect and store online content from different web pages. It extends the ConversableAgent class and provides additional functionality for managing a list of additional links, storing collected content in local directories, and customizing request headers.
    ContentAgent uses deque to manage a list of additional links for further exploration, with a maximum depth limit set by max_depth parameter. The collected content is stored in the specified storage path (storage_path) using local directories.
    ContentAgent can be customized with request_kwargs and llm_config parameters during instantiation. The default User-Agent header is used for requests, but it can be overridden by providing a new dictionary of headers under request_kwargs.

    Parameters:
        request_kwargs (dict): A dictionary containing key-value pairs used to configure request parameters such as headers and other options.
        storage_path (str): The path where the collected content will be stored. Defaults to './content'.
        max_depth (int): Maximum depth limit for exploring additional links from a web page. Defaults to 1.
        page_loading_time (float): Time in seconds to wait before loading each web page. Defaults to 5.
        *args, **kwargs: Additional arguments and keyword arguments to be passed to the parent class ConversableAgent.

    Software Dependencies:
        - beautifulsoup4
        - pdfminer
        - selenium
        - arxiv
        - pillow

    """

    def __init__(self, silent=True, storage_path="./content", max_depth=1, page_loading_time=5, *args, **kwargs):
        self.browser_kwargs = kwargs.pop("browser_kwargs", {"browser": "firefox"})
        super().__init__(*args, **kwargs)

        self.additional_links = deque()
        self.link_depth = 0
        self.max_depth = max_depth
        self.local_dir = storage_path
        self.page_load_time = page_loading_time
        self.silent = silent
        self.request_kwargs = {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
            }
        }
        self.small_llm_config = kwargs["llm_config"]
        self.process_history = {}

        # Define the classifiers
        self.define_classifiers()

    def classifier_to_collector_reply(self, recipient, messages, sender, config):
        # Inner dialogue reply for boolean classification results
        last_message = messages[-1] if isinstance(messages, list) else messages
        _, rep = recipient.generate_oai_reply([last_message], sender)
        if "false" in rep.lower():
            rep = "False"
        elif "true" in rep.lower():
            rep = "True"
        else:
            rep = "False"
        return True, rep

    def define_classifiers(self):
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

    # Main entry point
    def collect_content(self, recipient, messages, sender, config):
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
            content_type, content = self.fetch_content(link)

        # Inform self that it has completed the root level of link(s)
        self.link_depth = 1
        if self.link_depth <= self.max_depth:
            while len(self.additional_links) > 0:
                additional_link = self.additional_links.pop()
                content_type, content = self.fetch_content(additional_link)
                all_links.append(all_links)

        self.link_depth = 0
        return (
            True,
            f"Success: archived the following links in your chosen location {self.local_dir}/ <-- {', '.join(all_links)}",
        )

    def fetch_content(self, link):
        # Parse the link
        parsed_url = urlparse(link)

        # A special case for arxiv links
        if "arxiv" in link and IS_ARXIV_CAPABLE:
            return "pdf", self.fetch_arxiv_content(parsed_url)

        elif parsed_url.path.endswith(".pdf"):
            return "pdf", self.fetch_pdf_content(link)

        else:
            return "html", self.fetch_html_content(link)

    def fetch_html_content(self, link):
        # Handle web page content (html)

        sd = {}  # submission_data
        sd["url"] = link

        # Establish the downloads folder
        sd["local_path"] = os.path.join(self.local_dir, get_file_path_from_url(link))
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
        self.browser.save_full_page_screenshot(sd["browser_screenshot_path"])

        sd["title"] = self.browser.title
        sd["html"] = self.browser.page_source

        # Write the HTML to disk for archival purposes
        with open(os.path.join(sd["local_path"], "index.html"), "w", encoding="utf-8") as f:
            f.write(str(self.browser.page_source))

        # Store the BS object
        sd["soup"] = BeautifulSoup(sd["html"], "html.parser")

        sd["content"] = self.identify_content(sd["soup"])

        # Save the content to a text file on disk
        with open(os.path.join(sd["local_path"], "content.txt"), "w") as f:
            for data in sd["content"]:  # Iterate over each record
                f.write(data + "\n")  # Write the content to the file

        # Save the original URL for convenience elsewhere (when parsing images)
        sd["soup"].url = link

        # Parse and store the Metadata
        sd["meta"] = self.identify_metadata(sd["soup"])  # [ data.attrs for data in sd['soup'].find_all("meta") ]

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
        self.collect_images(sd["soup"], sd["local_path"])

        # Close down the browser
        self.browser.quit()

        # Log the processed link, motivated by the unit test
        self.process_history[sd["url"]] = sd

        return "success"

    def fetch_pdf_content(self, link):
        local_pdf_path = os.path.join(self.local_dir, os.path.join(get_file_path_from_url(link), link.split("/")[-1]))
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

    def fetch_arxiv_content(self, link):
        # Identify the paper identification
        arxiv_id = link.path.split("/")[-1]

        # Define the local directory
        local_base_path = os.path.join(self.local_dir, get_file_path_from_url(link))
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

    def identify_content(self, soup):
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

    def identify_metadata(self, soup, verbose=False):
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

    def collect_images(self, soup, local_path, verbose=False):
        def get_basename(filename):
            return os.path.splitext(os.path.basename(filename))[0]

        for img in soup.find_all("img"):
            img_alt = img.attrs["alt"] if "alt" in img.attrs else ""
            img_src = img.attrs["src"].lower()

            if "png;base64" in img_src:
                from io import BytesIO
                from PIL import Image
                import base64

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
