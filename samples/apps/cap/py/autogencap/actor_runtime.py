from abc import ABC, abstractmethod
from typing import List

from ._actor import Actor
from .actor_connector import IActorConnector
from .proto.CAP_pb2 import ActorInfo


class IRuntime(ABC):
    @abstractmethod
    def register(self, actor: Actor):
        pass

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def find_by_topic(self, topic: str) -> IActorConnector:
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> IActorConnector:
        pass

    @abstractmethod
    def find_termination(self) -> IActorConnector:
        pass

    @abstractmethod
    def find_by_name_regex(self, name_regex) -> List[ActorInfo]:
        pass
