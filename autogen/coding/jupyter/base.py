from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass
class JupyterConnectionInfo:
    host: str
    use_https: bool
    port: int
    token: Optional[str]


@runtime_checkable
class JupyterConnectable(Protocol):
    @property
    def connection_info(self) -> JupyterConnectionInfo:
        pass
