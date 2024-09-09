from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class DocumentType(Enum):
    """
    Enum for supporting document type.
    """

    TEXT = auto()
    HTML = auto()
    PDF = auto()


@dataclass
class Document:
    """
    A wrapper of graph store query results.
    """

    doctype: DocumentType
    data: Optional[object] = None
    path_or_url: Optional[str] = ""
