from abc import ABC, abstractmethod
from typing import List

from .actor_connector import IActorConnector
from .proto.CAP_pb2 import ActorInfo


class IMsgActor(ABC):
    """Abstract base class for message based actors."""

    @abstractmethod
    def on_connect(self, runtime: "IRuntime"):
        """Called when the actor connects to the runtime."""
        pass

    @abstractmethod
    def on_txt_msg(self, msg: str, msg_type: str, receiver: str, sender: str) -> bool:
        """Handle incoming text messages."""
        pass

    @abstractmethod
    def on_bin_msg(self, msg: bytes, msg_type: str, receiver: str, sender: str) -> bool:
        """Handle incoming binary messages."""
        pass

    @abstractmethod
    def on_start(self):
        """Called when the actor starts."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the actor."""
        pass

    @abstractmethod
    def dispatch_message(self, message):
        """Dispatch the received message based on its type."""
        pass


class IMessageReceiver(ABC):
    """Abstract base class for message receivers. Implementations are runtime specific."""

    @abstractmethod
    def init(self, actor_name: str):
        """Initialize the message receiver."""
        pass

    @abstractmethod
    def add_listener(self, topic: str):
        """Add a topic to the message receiver."""
        pass

    @abstractmethod
    def get_message(self):
        """Retrieve a message from the runtime implementation."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the message receiver."""
        pass


# Abstract base class for the runtime environment
class IRuntime(ABC):
    """Abstract base class for the actor runtime environment."""

    @abstractmethod
    def register(self, actor: IMsgActor):
        """Register an actor with the runtime."""
        pass

    @abstractmethod
    def get_new_msg_receiver(self) -> IMessageReceiver:
        """Create and return a new message receiver."""
        pass

    @abstractmethod
    def connect(self):
        """Connect the runtime to the messaging system."""
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect the runtime from the messaging system."""
        pass

    @abstractmethod
    def find_by_topic(self, topic: str) -> IActorConnector:
        """Find an actor connector by topic."""
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> IActorConnector:
        """Find an actor connector by name."""
        pass

    @abstractmethod
    def find_termination(self) -> IActorConnector:
        """Find the termination actor connector."""
        pass

    @abstractmethod
    def find_by_name_regex(self, name_regex) -> List["ActorInfo"]:
        """Find actors by name using a regular expression."""
        pass
