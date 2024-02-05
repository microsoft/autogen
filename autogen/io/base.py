from contextlib import AbstractContextManager
from typing import Literal, Optional, Protocol, Tuple, Union, runtime_checkable

__all__ = ("OutputStream", "InputStream", "IOStream", "ANSIColor", "ansi_colors")

ANSIColor = Union[
    Literal["black"],
    Literal["red"],
    Literal["green"],
    Literal["yellow"],
    Literal["blue"],
    Literal["magenta"],
    Literal["cyan"],
    Literal["white"],
]


ansi_colors: Tuple[ANSIColor] = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")  # type: ignore[assignment]


@runtime_checkable
class OutputStream(Protocol):
    def print(self, data: str, *, end: Optional[str] = None, flush: bool = False) -> None:
        """Print data to the output stream.

        Args:
            data (str): The data to print.
            end (Optional[str], optional): The string to append to the end of the data. If None (default), newline '\n' is appended. Defaults to None.
            flush (bool, optional): Whether to flush the output stream. Defaults to False.

        """
        ...  # pragma: no cover

    def set_style(
        self,
        *,
        fg: Optional[ANSIColor] = None,
        bg: Optional[ANSIColor] = None,
        bold: Optional[bool] = None,
        dim: Optional[bool] = None,
        emphasis: Optional[bool] = None,
        underline: Optional[bool] = None,
        srikethrough: Optional[bool] = None,
    ) -> AbstractContextManager[None]:
        """Set the color of the output stream.

        Args:
            fg (Optional[Color], optional): The foreground color. Defaults to None.
            bg (Optional[Color], optional): The background color. Defaults to None.
            bold (Optional[bool], optional): Whether to bold the text. Defaults to None.
            dim (Optional[bool], optional): Whether to dim the text. Defaults to None.
            emphasis (Optional[bool], optional): Whether to emphasize the text. Defaults to None.
            underline (Optional[bool], optional): Whether to underline the text. Defaults to None.
            srikethrough (Optional[bool], optional): Whether to srikethrough the text. Defaults to None.

        Yields:
            Generator[None, None, None]: A generator that yields None.

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
