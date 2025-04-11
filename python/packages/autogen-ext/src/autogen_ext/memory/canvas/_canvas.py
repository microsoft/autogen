from abc import ABC, abstractmethod
from typing import Dict, Any, Union


class BaseCanvas(ABC):
    """
    An abstract protocol for "canvas" objects that maintain
    revision history for file-like data. Concrete subclasses
    can handle text, images, structured data, etc.
    """

    @abstractmethod
    def list_files(self) -> Dict[str, int]:
        """
        Returns a dict of filename -> latest revision number.
        """
        raise NotImplementedError

    @abstractmethod
    def get_latest_content(self, filename: str) -> Union[str, bytes, Any]:
        """
        Returns the latest version of a file's content.
        """
        raise NotImplementedError

    @abstractmethod
    def add_or_update_file(self, filename: str, new_content: Union[str, bytes, Any]) -> None:
        """
        Creates or updates the file content with a new revision.
        """
        raise NotImplementedError

    @abstractmethod
    def get_diff(self, filename: str, from_revision: int, to_revision: int) -> str:
        """
        Returns a diff (in some format) between two revisions.
        """
        raise NotImplementedError

    @abstractmethod
    def apply_patch(self, filename: str, patch_data: Union[str, bytes, Any]) -> None:
        """
        Applies a patch/diff to the latest revision and increments the revision.
        """
        raise NotImplementedError
