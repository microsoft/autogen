from typing import Any

from autogen.io import IOConsole, IOStream, IOWebsockets


class TestIOStream:
    def test_initial_default_io_stream(self) -> None:
        assert isinstance(IOStream.get_default(), IOConsole)

    def test_set_default_io_stream(self) -> None:
        class MyIOStream(IOStream):
            def print(self, *objects: Any, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
                pass

            def input(self, prompt: str = "", *, password: bool = False) -> str:
                return "Hello, World!"

        assert isinstance(IOStream.get_default(), IOConsole)

        with IOStream.set_default(MyIOStream()):
            assert isinstance(IOStream.get_default(), MyIOStream)

            with IOStream.set_default(IOConsole()):
                assert isinstance(IOStream.get_default(), IOConsole)

            assert isinstance(IOStream.get_default(), MyIOStream)

        assert isinstance(IOStream.get_default(), IOConsole)
