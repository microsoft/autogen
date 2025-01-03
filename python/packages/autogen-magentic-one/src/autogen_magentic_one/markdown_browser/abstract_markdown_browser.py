from abc import ABC, abstractmethod
from typing import Union


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
    def __init__(self) -> None:
        pass

    @property
    @abstractmethod
    def address(self) -> str:
        pass

    @abstractmethod
    def set_address(self, uri_or_path: str) -> None:
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
    def page_down(self) -> None:
        pass

    @abstractmethod
    def page_up(self) -> None:
        pass

    @abstractmethod
    def visit_page(self, path_or_uri: str) -> str:
        pass

    @abstractmethod
    def open_local_file(self, local_path: str) -> str:
        pass

    @abstractmethod
    def find_on_page(self, query: str) -> Union[str, None]:
        pass

    @abstractmethod
    def find_next(self) -> Union[str, None]:
        pass

    @abstractmethod
    def extract_tables(self) -> list:
        """
        Extract tables from the Markdown content and return them as Python objects.
        """
        pass

    @abstractmethod
    def wait_for_render(self, timeout: int) -> None:
        """
        Wait for the dynamic content to render within the specified timeout.
        """
        pass

    @abstractmethod
    def get_logs(self) -> list:
        """
        Retrieve logs of browser activities and errors.
        """
        pass


