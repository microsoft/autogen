import asyncio
from abc import ABC, abstractmethod

from autogen_core import Component, ComponentBase, ComponentModel
from pydantic import BaseModel

class MessageCompletionException(BaseException): ...

class MessageCompletionCondition(ABC, ComponentBase[BaseModel]):
    pass