from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Optional, Protocol, runtime_checkable

from pydantic import BaseModel

__all__ = ("OutputStream", "InputStream", "IOStream")


@runtime_checkable
class OutputStream(Protocol):
    def print(self, *objects: Any, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
        """Print data to the output stream.

        Args:
            objects (any): The data to print.
            sep (str, optional): The separator between objects. Defaults to " ".
            end (str, optional): The end of the output. Defaults to "\n".
            flush (bool, optional): Whether to flush the output. Defaults to False.
        """
        ...  # pragma: no cover

    def output(self, msg: BaseModel) -> None:
        """Output a JSON-enocded message to the output stream.

        Args:
            msg (BaseModel): The message to output.
        """
        ...


@runtime_checkable
class InputStream(Protocol):
    def input(self, prompt: str = "", *, password: bool = False) -> str:
        """Read a line from the input stream.

        Args:
            prompt (str, optional): The prompt to display. Defaults to "".
            password (bool, optional): Whether to read a password. Defaults to False.

        Returns:
            str: The line read from the input stream.

        """
        ...  # pragma: no cover


@runtime_checkable
class IOStream(InputStream, OutputStream, Protocol):
    """A protocol for input/output streams."""

    @staticmethod
    def get_default() -> "IOStream":
        """Get the default input/output stream.

        Returns:
            IOStream: The default input/output stream.
        """
        iostream = IOStream._default_io_stream.get(None)
        if iostream is None:
            raise RuntimeError("No default IOStream has been set")

        return iostream

    # ContextVar must be used in multithreaded or async environments
    _default_io_stream: ContextVar[Optional["IOStream"]] = ContextVar("default_iostream")
    _default_io_stream.set(None)

    @staticmethod
    @contextmanager
    def set_default(iostream: Optional["IOStream"]) -> Iterator[None]:
        """Set the default input/output stream.

        Args:
            stream (IOStream): The input/output stream to set as the default.
        """
        global _default_io_stream
        try:
            token = IOStream._default_io_stream.set(iostream)

            if IOStream.get_default() != iostream:
                raise RuntimeError("Failed to set default IOStream")

            yield
        finally:
            IOStream._default_io_stream.reset(token)

        return
