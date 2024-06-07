from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass
class JupyterConnectionInfo:
    """(Experimental)"""

    host: str
    """`str` - Host of the Jupyter gateway server"""
    use_https: bool
    """`bool` - Whether to use HTTPS"""
    port: Optional[int] = None
    """`Optional[int]` - Port of the Jupyter gateway server. If None, the default port is used"""
    token: Optional[str] = None
    """`Optional[str]` - Token for authentication. If None, no token is used"""


@runtime_checkable
class JupyterConnectable(Protocol):
    """(Experimental)"""

    @property
    def connection_info(self) -> JupyterConnectionInfo:
        """Return the connection information for this connectable."""
        pass
