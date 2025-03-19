import json
import hashlib
import re
from typing import Protocol, List, Set, Optional
from pydantic import BaseModel


class Document(BaseModel):
    text: str
    name: Optional[str] = None

    def __hash__(self) -> int:
        return int(hashlib.md5(self.text.encode("utf-8")).hexdigest(), 16)


class CodeExample(BaseModel):
    """
    Represents an example associated with a code.

    Attributes:
        line (int): The line number in the file where the code example starts.
        line_end (int): The line number in the file  where the code example ends.
        reason (str): A description explaining the purpose or context of the
        code example.
    """

    line: int
    line_end: int
    reason: str


class Code(BaseModel):
    name: str
    definition: str
    examples: List[CodeExample]  # changed from List[str]
    id: Optional[int] = None
    merged_from: Optional[List[int]] = None

    def __init__(
        self,
        name: str,
        definition: str,
        examples: List[CodeExample],
        id: Optional[int] = None,
        merged_from: Optional[List[int]] = None,
    ):
        super().__init__(name=name, definition=definition, examples=examples)
        self.name = re.sub(r"[^a-z-]", "", self.name.lower().replace(" ", "-"))
        self.id = int(
            hashlib.md5((self.name + self.definition).encode("utf-8")).hexdigest(), 16
        )
        self.merged_from = None

    def __hash__(self) -> int:
        if self.id is None:
            raise ValueError("Code ID is not set.")
        return self.id

    def add_merged_from(self, code_id: int) -> None:
        if self.merged_from is None:
            self.merged_from = []
        if code_id not in self.merged_from:
            self.merged_from.append(code_id)


class CodedDocument(BaseModel):
    doc: Document
    codes: Set[Code]

    @classmethod
    def from_json(cls, json_str: str) -> "CodedDocument":
        data = json.loads(json_str)
        doc = Document(**data["doc"])
        codes = {Code(**code) for code in data["codes"]}
        return cls(doc=doc, codes=codes)


class BaseQualitativeCoder(Protocol):
    def code_document(
        self, doc: Document, code_set: Optional[Set[Code]]
    ) -> Optional[CodedDocument]: ...
