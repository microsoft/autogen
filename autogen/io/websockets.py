from contextlib import contextmanager
from typing import Any, Iterator, Optional

from .base import IOStream

# Check if the websockets module is available
try:
    import websockets
    from websockets.sync.client import connect, ClientConnection
except ImportError as e:
    websockets = None  # type: ignore[assignment]
    connect = None  # type: ignore[assignment]
    _import_error = e
else:
    _import_error = None  # type: ignore[assignment]


__all__ = ("IOWebsockets",)


class IOWebsockets(IOStream):
    """A websocket input/output stream."""

    def __init__(self, websocket: "ClientConnection") -> None:
        """Initialize the websocket input/output stream.

        Args:
            uri (str, optional): The URI of the websocket server. Defaults to "ws://localhost:8765".

        Raises:
            ImportError: If the websockets module is not available.
        """
        if websockets is None:
            raise _import_error

        self._websocket = websocket

    @contextmanager
    def connect(cls, uri: Optional[str] = None) -> Iterator["IOWebsockets"]:
        """Factory function to create a websocket input/output stream.

        Args:
            uri (str, optional): The URI of the websocket server. Defaults to "ws://localhost:8765".

        Yields:
            IOWebsockets: The websocket input/output stream.
        """
        url = uri or "ws://localhost:8765"

        with connect(url) as ws:
            yield cls(ws)  # type: ignore[operator]

    @property
    def websocket(self) -> "ClientConnection":
        """The URI of the websocket server."""
        return self._websocket

    def print(self, *objects: Any, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
        """Print data to the output stream.

        Args:
            objects (any): The data to print.
            sep (str, optional): The separator between objects. Defaults to " ".
            end (str, optional): The end of the output. Defaults to "\n".
            flush (bool, optional): Whether to flush the output. Defaults to False.
        """
        xs = sep.join(map(str, objects)) + end
        self._websocket.send(xs)

    def input(self, prompt: str = "", *, password: bool = False) -> str:
        """Read a line from the input stream.

        Args:
            prompt (str, optional): The prompt to display. Defaults to "".
            password (bool, optional): Whether to read a password. Defaults to False.

        Returns:
            str: The line read from the input stream.

        """
        raise NotImplementedError
