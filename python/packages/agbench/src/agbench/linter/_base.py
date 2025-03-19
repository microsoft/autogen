import json
import hashlib
import re
from typing import Protocol, List, Set, Optional
from pydantic import BaseModel, Field


class Document(BaseModel):
    text: str = Field(..., description="Text content of the document.")
    name: Optional[str] = Field(None, description="Optional name of the document.")

    def __hash__(self) -> int:
        return int(hashlib.md5(self.text.encode("utf-8")).hexdigest(), 16)


class CodeExample(BaseModel):
    """
    Represents an example associated with a code.
    """

    reason: str = Field(
        ..., description="A two sentence, human-readable explanation why this example and lines relate to the code."
    )
    line_content: str = Field(
        ..., description="The exact content of the line where the error is found. This should be a single line."
    )
    line: int = Field(..., description="The most important line number where a human would say the error is.")
    line_end: int = Field(..., description="Line number where the issue ends.")


class Code(BaseModel):
    name: str = Field(..., description="Normalized unique name for the code (lowercase, hyphen separated).")
    definition: str = Field(..., description="Definition of the code.")
    examples: List[CodeExample] = Field(
        ..., description="List of code examples associated with the code. Cannot be empty."
    )
    severity: int = Field(
        ..., description="Severity rating of the error identified using the code. Valid values: 0, 1, 2."
    )
    id: Optional[int] = Field(None, description="Identifier computed using MD5 of name and definition.")
    merged_from: Optional[List[int]] = Field(None, description="List of code ids from which this code is merged.")

    def __init__(
        self,
        name: str,
        definition: str,
        examples: List[CodeExample],
        severity: int,
        id: Optional[int] = None,
        merged_from: Optional[List[int]] = None,
    ):
        super().__init__(name=name, definition=definition, examples=examples, severity=severity)
        self.name = re.sub(r"[^a-z-]", "", self.name.lower().replace(" ", "-"))
        self.id = int(hashlib.md5((self.name + self.definition).encode("utf-8")).hexdigest(), 16)
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
    def code_document(self, doc: Document, code_set: Optional[Set[Code]]) -> Optional[CodedDocument]: ...
