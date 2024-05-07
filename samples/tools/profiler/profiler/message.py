from dataclasses import dataclass
from typing import List


@dataclass
class Message:
    """A message with a source, role, and content."""

    source: str
    role: str
    content: str
    tags: List[str] = None
    id: str = None

    def to_dict(self):
        return {"id": self.id, "source": self.source, "role": self.role, "content": self.content, "tags": self.tags}


@dataclass
class OpenAIMessage:
    """A message with a role and content, as required by OpenAI API."""

    role: str
    content: str

    def to_dict(self):
        return {"role": self.role, "content": self.content}
