from typing import Any, Protocol, runtime_checkable

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
