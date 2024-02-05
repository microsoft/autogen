from typing import Any, ContextManager, Literal, Optional, Protocol, Tuple, Union, runtime_checkable

__all__ = ("OutputStream", "InputStream", "IOStream")


@runtime_checkable
class OutputStream(Protocol):
    def print(self, *objects: Any, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
        """Print data to the output stream.

        Args:
            objects (any): The data to print.
            sep (str, optional): The string to separate the data. Defaults to " ".
            end (str, optional): The string to append to the end of the data. If None (default), newline '\n' is appended. Defaults to None.
            flush (bool, optional): Whether to flush the output stream. Defaults to False.
        """
        ...  # pragma: no cover


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

    ...  # pragma: no cover
