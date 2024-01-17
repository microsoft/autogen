import abc
import socketio
from typing import Union, Tuple, Any, Optional, Dict


class StreamHandler(abc.ABC):
    """
    Abstract base class for streaming data.
    """

    @abc.abstractmethod
    def open(self):
        """
        Open the stream.
        """
        pass

    @abc.abstractmethod
    def write(self, data):
        """
        Write data to the stream.
        """
        pass

    @abc.abstractmethod
    def close(self):
        """
        Close the stream.
        """
        pass


class SimpleClientSocketIOStreamHandler(StreamHandler):
    """
    A StreamHandler implementation using socketio's SimpleClient for streaming data.
    """

    def __init__(self, socket_client: socketio.simple_client.SimpleClient):
        """
        Initialize the SimpleClientSocketIOStreamHandler with a SimpleClient instance.
        """
        # Check input type
        if not isinstance(socket_client, socketio.simple_client.SimpleClient):
            raise TypeError("socket_client must be a socketio.simple_client.SimpleClient instance.")

        super().__init__()
        self.socket_client = socket_client

    def open(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Dict[str, Any]] = None,
        transports: Optional[list] = None,
        namespace: str = "/",
        socketio_path: str = "socket.io",
        wait_timeout: int = 5,
    ) -> None:
        """
        Connect to a Socket.IO server.
        :param url: URL of the Socket.IO server.
        :param headers: Optional dictionary with custom headers.
        :param auth: Optional authentication data.
        :param transports: Optional list of allowed transports.
        :param namespace: Namespace to connect to.
        :param socketio_path: Socket.IO server endpoint.
        :param wait_timeout: Timeout for establishing connection.
        """
        self.socket_client.connect(url, headers, auth, transports, namespace, socketio_path, wait_timeout)

    def write(self, event: str, data: Union[str, bytes, list, dict, Tuple[Any, ...]]) -> None:
        """
        Send data over the socket.
        :param event: The name of the event. It must be a string.
        :param data: The data to send. Can be a str, bytes, list, dict, or a tuple containing these types.
        """
        self.socket_client.emit(event, data)

    def close(self) -> None:
        """
        Disconnect from the server.
        """
        self.socket_client.disconnect()
