from typing import Protocol, runtime_checkable

from ._jupyter_client import JupyterClient
from ._jupyter_connection_info import JupyterConnectionInfo


@runtime_checkable
class JupyterConnectable(Protocol):
    """TODO"""

    @property
    def connection_info(self) -> JupyterConnectionInfo:
        """Return the connection information for this connectable."""
        ...

    def get_client(self) -> JupyterClient:
        """Return the jupyter client using the connection info."""
        return JupyterClient(self.connection_info)
