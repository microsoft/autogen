import getpass
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from .base import IOStream

__all__ = ("IOConsole",)


@runtime_checkable
class ConsoleMessage(Protocol):
    """A protocol for console messages."""

    def to_console(self) -> str:
        """Convert the message to a console message."""
        ...


class IOConsole(IOStream):
    """A console input/output stream."""

    def print(self, *objects: Any, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
        """Print data to the output stream.

        Args:
            objects (any): The data to print.
            sep (str, optional): The separator between objects. Defaults to " ".
            end (str, optional): The end of the output. Defaults to "\n".
            flush (bool, optional): Whether to flush the output. Defaults to False.
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
            return getpass.getpass(prompt if prompt != "" else "Password: ")
        return input(prompt)

    def output(self, msg: BaseModel) -> None:
        """Output a JSON-enocded message to the output stream.

        Args:
            msg (BaseModel): The message to output.
        """
        # if msg implements ConsoleMessage protocol, use that. If not, use the model_dump_json method
        if isinstance(msg, ConsoleMessage):
            print(msg.to_console())
        else:
            print(msg.model_dump_json(indent=2))
