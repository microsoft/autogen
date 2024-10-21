from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple


class IActorConnector(ABC):
    """
    Abstract base class for actor connectors.  Each runtime will have a different implementation.
    Obtain an instance of the correct connector from the runtime by calling the runtime's find_by_xyz
    method.
    """

    @abstractmethod
    def send_txt_msg(self, msg: str) -> None:
        """
        Send a text message to the actor.

        Args:
            msg (str): The text message to send.
        """
        pass

    @abstractmethod
    def send_bin_msg(self, msg_type: str, msg: bytes) -> None:
        """
        Send a binary message to the actor.

        Args:
            msg_type (str): The type of the binary message.
            msg (bytes): The binary message to send.
        """
        pass

    @abstractmethod
    def send_proto_msg(self, msg: Any) -> None:
        """
        Send a protocol buffer message to the actor.

        Args:
            msg (Any): The protocol buffer message to send.
        """
        pass

    @abstractmethod
    def send_recv_proto_msg(
        self, msg: Any, num_attempts: int = 5
    ) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
        """
        Send a protocol buffer message and receive a response from the actor.

        Args:
            msg (Any): The protocol buffer message to send.
            num_attempts (int, optional): Number of attempts to send and receive. Defaults to 5.

        Returns:
            Tuple[Optional[str], Optional[str], Optional[bytes]]: A tuple containing the topic,
            message type, and response message, or None if no response is received.
        """
        pass

    @abstractmethod
    def send_recv_msg(
        self, msg_type: str, msg: bytes, num_attempts: int = 5
    ) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
        """
        Send a binary message and receive a response from the actor.

        Args:
            msg_type (str): The type of the binary message.
            msg (bytes): The binary message to send.
            num_attempts (int, optional): Number of attempts to send and receive. Defaults to 5.

        Returns:
            Tuple[Optional[str], Optional[str], Optional[bytes]]: A tuple containing the topic,
            message type, and response message, or None if no response is received.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close the actor connector and release any resources.
        """
        pass
