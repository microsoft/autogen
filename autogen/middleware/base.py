from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class AbstractMiddleWare(ABC):
    @abstractmethod
    def on_enter(self, x: Any):
        pass

    @abstractmethod
    def on_exit(self, x: Any):
        pass
