
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic.dataclasses import dataclass

@dataclass
class Message(object):
    userId: str 
    role: str
    content: str 
    rootMsgId: Optional[str] = None
    msgId: Optional[str] = None
    timestamp: Optional[datetime] = None
    use_cache: Optional[bool] = False
    personalize: Optional[bool] = False
    ra:  Optional[str] = None
    code: Optional[str] = None  
    metadata: Optional[Any] = None

    def __post_init__(self):
        if self.msgId is None:
            self.msgId = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()
    def dict(self):
        return {
            "userId": self.userId,
            "role": self.role,
            "content": self.content,
            "rootMsgId": self.rootMsgId,
            "msgId": self.msgId,
            "timestamp": self.timestamp,
            "use_cache": self.use_cache,
            "personalize": self.personalize,
            "ra": self.ra,
            "code": self.code,
            "metadata": self.metadata,
        }
@dataclass
class DeleteMessageModel(object):
    userId: str
    msgId: str

@dataclass
class ClearDBModel(object):
    userId: str    