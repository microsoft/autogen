from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional

class IActorConnector(ABC):
    @abstractmethod
    def send_txt_msg(self, msg: str) -> None:
        pass

    @abstractmethod
    def send_bin_msg(self, msg_type: str, msg: bytes) -> None:
        pass

    @abstractmethod
    def send_proto_msg(self, msg: Any) -> None:
        pass

    @abstractmethod
    def send_recv_proto_msg(self, msg: Any, num_attempts: int = 5) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
        pass

    @abstractmethod
    def send_recv_msg(self, msg_type: str, msg: bytes, num_attempts: int = 5) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
