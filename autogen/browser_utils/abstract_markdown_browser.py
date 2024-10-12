from abc import ABC, abstractmethod
from typing import Dict, Optional, Union


class AbstractMarkdownBrowser(ABC):
    """
    An abstract class for a Markdown web browser.

    All MarkdownBrowers work by:

        (1) fetching a web page by URL (via requests, Selenium, Playwright, etc.)
        (2) converting the page's HTML or DOM to Markdown
        (3) operating on the Markdown

    Such browsers are simple, and suitable for read-only agentic use.
    They cannot be used to interact with complex web applications.
    """

    @abstractmethod
    def __init__(self):
        pass

    @property
    @abstractmethod
    def address(self) -> str:
        pass

    @abstractmethod
    def set_address(self, uri_or_path):
        pass

    @property
    @abstractmethod
    def viewport(self) -> str:
        pass

    @property
    @abstractmethod
    def page_content(self) -> str:
        pass

    @abstractmethod
    def page_down(self):
        pass

    @abstractmethod
    def page_up(self):
        pass

    @abstractmethod
    def visit_page(self, path_or_uri):
        pass

    @abstractmethod
    def open_local_file(self, local_path):
        pass

    @abstractmethod
    def find_on_page(self, query: str):
        pass

    @abstractmethod
    def find_next(self):
        pass
