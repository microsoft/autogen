import asyncio
from contextlib import AbstractAsyncContextManager, asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator
from unittest.mock import patch, MagicMock

import pytest

from autogen.io import IOWebsockets

# Check if the websockets module is available
try:
    import websockets
    from websockets.server import WebSocketServerProtocol, serve
    import websockets.client
except ImportError:  # pragma: no cover
    websockets = None  # type: ignore[assignment]
    skip_test = True
else:
    skip_test = False


class TestConsoleIOWithWebsockets:
    async def _run_server(self) -> None:
        # this function will be called when a meesage if received on the incoming websocket
        self.ws = None
        self.shutdown = False
        self.serve_mock = MagicMock()
        self.server_send_message = MagicMock(return_value="Hello, World!")

        async def _serve(websocket: "WebSocketServerProtocol") -> None:
            async for message in websocket:
                self.serve_mock(message)
                msg = self.server_send_message(message)
                await websocket.send(msg)

        # find an available port to run the server
        for port in range(8765, 8765 + 100):
            try:
                async with serve(_serve, "127.0.0.1", port) as ws:
                    self.ws = ws
                    self.port = port
                    while not self.shutdown:
                        await asyncio.sleep(0.1)

                    self.ws.close()
                    await self.ws.wait_closed()

                    return None
            except Exception as e:
                print(f"Port {port} is not available: {e}")
                continue

        raise RuntimeError("No available port for testing")

    @asynccontextmanager
    async def run_server(self) -> AsyncIterator[str]:
        # start server
        task = asyncio.create_task(self._run_server())
        print("Waiting for server to start", end="", flush=True)
        while not hasattr(self, "ws") or not self.ws:
            print(".", end="", flush=True)
            print()
            await asyncio.sleep(0.1)

        # yield control to the test
        yield f"ws://127.0.0.1:{self.port}"

        # gracefully stop server
        self.shutdown = True
        await task

    @pytest.mark.asyncio()
    async def test_setup(self) -> None:
        async with self.run_server() as uri:
            print(f"Running server on {uri}.", flush=True)

            print(f"Connecting client to server on {uri}.", flush=True)
            async with websockets.client.connect(uri) as websocket:
                print(f"Connected to server on {uri}", flush=True)

                print("Sending message to server.", flush=True)
                self.server_send_message = MagicMock(return_value="Whatsup!")
                await websocket.send("Hello world!")

                print("Receiving message from server.", flush=True)
                message = await websocket.recv()

                print("Asserting received message is as expected.", flush=True)
                assert message == "Whatsup!"

    @pytest.mark.asyncio()
    async def test_connect(self) -> None:
        async with self.run_server() as uri:
            with IOWebsockets.connect(uri) as console_io:
                assert console_io.websocket is not None

    # @pytest.mark.skipif(skip_test, reason="websockets module is not available")
    # @patch("builtins.print")
    # def test_print(self, mock_print: MagicMock) -> None:
    #     # calling the print method should call the mock of the builtin print function
    #     self.console_io.print("Hello, World!", flush=True)
    #     mock_print.assert_called_once_with("Hello, World!", end="\n", sep=" ", flush=True)

    # @pytest.mark.skipif(skip_test, reason="websockets module is not available")
    # @patch("builtins.input")
    # def test_input(self, mock_input: MagicMock) -> None:
    #     # calling the input method should call the mock of the builtin input function
    #     mock_input.return_value = "Hello, World!"

    #     actual = self.console_io.input("Hi!")
    #     assert actual == "Hello, World!"
    #     mock_input.assert_called_once_with("Hi!")

    # @pytest.mark.skipif(skip_test, reason="websockets module is not available")
    # @pytest.mark.parametrize("prompt", ["", "Password: ", "Enter you password:"])
    # def test_input_password(self, monkeypatch: pytest.MonkeyPatch, prompt: str) -> None:
    #     mock_getpass = MagicMock()
    #     mock_getpass.return_value = "123456"
    #     monkeypatch.setattr("getpass.getpass", mock_getpass)

    #     actual = self.console_io.input(prompt, password=True)
    #     assert actual == "123456"
    #     if prompt == "":
    #         mock_getpass.assert_called_once_with("Password: ")
    #     else:
    #         mock_getpass.assert_called_once_with(prompt)
