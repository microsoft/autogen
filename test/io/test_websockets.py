from contextlib import AbstractContextManager, contextmanager
import threading
from time import sleep
from typing import Iterator
from unittest.mock import MagicMock

import pytest

from autogen.io import IOWebsockets

# Check if the websockets module is available
try:
    from websockets.sync.server import ServerConnection, serve
    from websockets.sync.client import connect
except ImportError:  # pragma: no cover
    skip_test = True
else:
    skip_test = False


class TestConsoleIOWithWebsockets:
    def _run_server(self) -> None:
        self.ws = None
        self.serve_mock = MagicMock()
        self.server_send_message = MagicMock(return_value="Hello, World!")

        # this function will be called when a meesage if received on the incoming websocket
        def _serve(websocket: "ServerConnection") -> None:
            for message in websocket:
                message = message.decode("utf-8") if isinstance(message, bytes) else message
                print(f" - Message received on the server: {message}", flush=True)
                self.serve_mock(message)
                msg = self.server_send_message(message)
                websocket.send(msg)

        # find an available port to run the server
        for port in range(8765, 8765 + 100):
            try:
                with serve(_serve, "127.0.0.1", port) as ws:
                    self.port = port
                    self.uri = f"ws://127.0.0.1:{port}"
                    self.ws = ws

                    # runs until the server is shutdown
                    self.ws.serve_forever()

                    return

            except Exception as e:
                print(f"Port {port} is not available: {e}")
                continue

        raise RuntimeError("No available port for testing")

    @pytest.fixture
    @contextmanager
    def server(self) -> Iterator[str]:
        # start server in a separate thread
        thread = threading.Thread(target=self._run_server)
        thread.start()
        try:
            while not hasattr(self, "ws") or not self.ws:
                sleep(0.1)

            # yield control to the test
            yield f"ws://127.0.0.1:{self.port}"

        finally:
            # gracefully stop server
            if hasattr(self, "ws") and self.ws:
                self.ws.shutdown()

            # wait for the thread to stop
            if thread:
                thread.join()

    @pytest.mark.skipif(skip_test, reason="websockets module is not available")
    def test_setup(self, server: "AbstractContextManager[str]") -> None:
        print("Testing setup", flush=True)
        with server as uri:
            print(f"test_setup() with websocket server running of {uri}.", flush=True)
            with connect(uri) as websocket:
                print(f" - Connected to server on {uri}", flush=True)

                print(" - Sending message to server.", flush=True)
                self.server_send_message = MagicMock(return_value="Whatsup!")
                websocket.send("Hello world!")

                print(" - Receiving message from server.", flush=True)
                message = websocket.recv()
                message = message.decode("utf-8") if isinstance(message, bytes) else message

                print(
                    f" - Asserting received message '{message}' is the same as the expected message 'Whatsup!'",
                    flush=True,
                )
                assert message == "Whatsup!"

                print(" - Test passed.", flush=True)

    @pytest.mark.skipif(skip_test, reason="websockets module is not available")
    def test_print(self, server: "AbstractContextManager[str]") -> None:
        print("Testing print", flush=True)
        # starts the server
        with server as uri:
            print(f"test_print() with websocket server running of {uri}.", flush=True)
            with IOWebsockets.connect(uri) as iostream:
                print(f" - Connected to server on {uri}", flush=True)

                print(" - Checking if the websocket is accessible through property.", flush=True)
                assert iostream.websocket is not None

                print(" - Sending message to server.", flush=True)
                iostream.print("Hello, World!")

                print(" - Sleeping for 1 second.", flush=True)
                sleep(1)
                print(" - Checking if the server received the message.", flush=True)
                self.serve_mock.assert_called_once_with("Hello, World!\n")

                print(" - Test passed.", flush=True)

    @pytest.mark.skipif(skip_test, reason="websockets module is not available")
    def test_input(self, server: "AbstractContextManager[str]") -> None:
        print("Testing input", flush=True)
        # starts the server
        with server as uri:
            print(f"test_input() with websocket server running of {uri}.", flush=True)
            with IOWebsockets.connect(uri) as iostream:
                print(f" - Connected to server on {uri}", flush=True)

                # mock the server response
                self.server_send_message.return_value = "4"
                print(" - Request message to server.", flush=True)
                actual = iostream.input("2+2=?")

                print(" - Checking if the server received the message.", flush=True)
                self.serve_mock.assert_called_once_with("2+2=?")

                print(f" - Asserting received message '{actual}' is the same as the expected message '4'", flush=True)
                assert actual == "4"

                print(" - Test passed.", flush=True)
