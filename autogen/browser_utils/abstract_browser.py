from abc import ABC, abstractmethod
from typing import Optional, Union, Dict


class AbstractBrowser(ABC):
    """An abstract class for a web browser."""

    @abstractmethod
    def __init__(
        self,
        start_page: Optional[str] = "about:blank",
        viewport_size: Optional[int] = 1024 * 8,
        downloads_folder: Optional[Union[str, None]] = None,
        bing_api_key: Optional[Union[str, None]] = None,
        request_kwargs: Optional[Union[Dict, None]] = None,
    ):
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
