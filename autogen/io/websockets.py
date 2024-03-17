import logging
import ssl
import threading
from contextlib import contextmanager
from functools import partial
from time import sleep
from typing import Any, Callable, Dict, Iterator, Optional

from .base import IOStream

# Check if the websockets module is available
try:
    import websockets
    from websockets.sync.server import ServerConnection, WebSocketServer
    from websockets.sync.server import serve as ws_serve
except ImportError as e:  # pragma: no cover
    websockets = None  # type: ignore[assignment]
    ws_serve = None  # type: ignore[assignment]
    _import_error: Optional[ImportError] = e
else:
    _import_error = None


__all__ = ("IOWebsockets",)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IOWebsockets(IOStream):
    """A websocket input/output stream."""

    def __init__(self, websocket: "ServerConnection") -> None:
        """Initialize the websocket input/output stream.

        Args:
            websocket (ServerConnection): The websocket server.

        Raises:
            ImportError: If the websockets module is not available.
        """
        if websockets is None:
            raise _import_error  # pragma: no cover

        self._websocket = websocket

    @staticmethod
    def _handler(websocket: "ServerConnection", on_connect: Callable[["IOWebsockets"], None]) -> None:
        """The handler function for the websocket server."""
        logger.info(f" - IOWebsockets._handler(): Client connected on {websocket}")
        # create a new IOWebsockets instance using the websocket that is create when a client connects
        try:
            iowebsocket = IOWebsockets(websocket)
            with IOStream.set_default(iowebsocket):
                # call the on_connect function
                try:
                    on_connect(iowebsocket)
                except Exception as e:
                    logger.warning(f" - IOWebsockets._handler(): Error in on_connect: {e}")
        except Exception as e:
            logger.error(f" - IOWebsockets._handler(): Unexpected error in IOWebsockets: {e}")

    @staticmethod
    @contextmanager
    def run_server_in_thread(
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        on_connect: Callable[["IOWebsockets"], None],
        ssl_context: Optional[ssl.SSLContext] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Factory function to create a websocket input/output stream.

        Args:
            host (str, optional): The host to bind the server to. Defaults to "127.0.0.1".
            port (int, optional): The port to bind the server to. Defaults to 8765.
            on_connect (Callable[[IOWebsockets], None]): The function to be executed on client connection. Typically creates agents and initiate chat.
            ssl_context (Optional[ssl.SSLContext], optional): The SSL context to use for secure connections. Defaults to None.

        Yields:
            str: The URI of the websocket server.
        """
        server_dict: Dict[str, WebSocketServer] = {}

        def _run_server() -> None:
            # print(f" - _run_server(): starting server on ws://{host}:{port}", flush=True)
            with ws_serve(
                handler=partial(IOWebsockets._handler, on_connect=on_connect),
                host=host,
                port=port,
                ssl_context=ssl_context,
                **kwargs,
            ) as server:
                # print(f" - _run_server(): server {server} started on ws://{host}:{port}", flush=True)

                server_dict["server"] = server

                # runs until the server is shutdown
                server.serve_forever()

                return

        # start server in a separate thread
        thread = threading.Thread(target=_run_server)
        thread.start()
        try:
            while "server" not in server_dict:
                sleep(0.1)

            yield f"ws://{host}:{port}"

        finally:
            # print(f" - run_server_in_thread(): shutting down server on ws://{host}:{port}", flush=True)
            # gracefully stop server
            if "server" in server_dict:
                # print(f" - run_server_in_thread(): shutting down server {server_dict['server']}", flush=True)
                server_dict["server"].shutdown()

            # wait for the thread to stop
            if thread:
                thread.join()

    @property
    def websocket(self) -> "ServerConnection":
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
        if prompt != "":
            self._websocket.send(prompt)

        msg = self._websocket.recv()

        return msg.decode("utf-8") if isinstance(msg, bytes) else msg
