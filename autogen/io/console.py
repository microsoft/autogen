import getpass
from typing import Any

from .base import IOStream

__all__ = ("IOConsole",)


class IOConsole(IOStream):
    """A console input/output stream."""

    def print(self, *objects: Any, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
        """Print data to the output stream.

        Args:
            data (str): The data to print.
            end (str, optional): The string to append to the end of the data. If None (default), newline '\n' is appended. Defaults to None.
            flush (bool, optional): Whether to flush the output stream. Defaults to False.

        """
        print(*objects, sep=sep, end=end, flush=flush)

    def input(self, prompt: str = "", *, password: bool = False) -> str:
        """Read a line from the input stream.

        Args:
            prompt (str, optional): The prompt to display. Defaults to "".
            password (bool, optional): Whether to read a password. Defaults to False.

        Returns:
            str: The line read from the input stream.

        """

        if password:
            return getpass.getpass()
        return input(prompt)
