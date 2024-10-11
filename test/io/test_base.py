from threading import Thread
from typing import Any, List

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

    def test_get_default_on_new_thread(self) -> None:
        exceptions: List[Exception] = []

        def on_new_thread(exceptions: List[Exception] = exceptions) -> None:
            try:
                assert isinstance(IOStream.get_default(), IOConsole)
            except Exception as e:
                exceptions.append(e)

        # create a new thread and run the function
        thread = Thread(target=on_new_thread)

        thread.start()

        # get exception from the thread
        thread.join()

        if exceptions:
            raise exceptions[0]
