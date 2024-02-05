from contextlib import contextmanager
import getpass
from collections import deque
from typing import Iterator, Optional, Deque, Tuple

from .base import IOStream, ANSIColor

__all__ = ("IOConsole",)


class IOConsole(IOStream):
    def __init__(self) -> None:
        self._prefix = ""
        self._color_stack: Deque[
            Tuple[
                Optional[ANSIColor],
                Optional[ANSIColor],
                Optional[bool],
                Optional[bool],
                Optional[bool],
                Optional[bool],
                Optional[bool],
            ]
        ] = deque()

    """A console input/output stream."""

    def print(self, data: str, *, end: Optional[str] = None, flush: bool = False) -> None:
        """Print data to the output stream.

        Args:
            data (str): The data to print.
            end (str, optional): The string to append to the end of the data. If None (default), newline '\n' is appended. Defaults to None.
            flush (bool, optional): Whether to flush the output stream. Defaults to False.

        """
        if end is None:
            end = "\n"
        print(self._prefix + data, end=end, flush=flush)
        self._prefix = ""

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

    _fg = dict(
        black="\u001b[30m",
        red="\u001b[31m",
        green="\u001b[32m",
        yellow="\u001b[33m",
        blue="\u001b[34m",
        magenta="\u001b[35m",
        cyan="\u001b[36m",
        white="\u001b[37m",
    )

    _bg = dict(
        black="\u001b[40m",
        red="\u001b[41m",
        green="\u001b[42m",
        yellow="\u001b[43m",
        blue="\u001b[44m",
        magenta="\u001b[45m",
        cyan="\u001b[46m",
        white="\u001b[47m",
    )

    _bold = "\u001b[1m"
    _dim = "\u001b[2m"
    _emphasis = "\u001b[3m"
    _underline = "\u001b[4m"
    _strikethrough = "\u001b[9m"

    _reset = "\u001b[0m"

    def _set_style(
        self,
        fg: Optional[ANSIColor],
        bg: Optional[ANSIColor],
        bold: Optional[bool],
        dim: Optional[bool],
        emphasis: Optional[bool],
        underline: Optional[bool],
        srikethrough: Optional[bool],
    ) -> None:
        cmd = ""
        if bold is not None:
            cmd += IOConsole._bold

        if dim is not None:
            cmd += IOConsole._dim

        if emphasis is not None:
            cmd += IOConsole._emphasis

        if underline is not None:
            cmd += IOConsole._underline

        if srikethrough is not None:
            cmd += IOConsole._strikethrough

        if fg is not None:
            cmd += IOConsole._fg[fg]

        if bg is not None:
            cmd += IOConsole._bg[bg]

        print(cmd, end="")

    def _get_styles(
        self,
        fg: Optional[ANSIColor],
        bg: Optional[ANSIColor],
        bold: Optional[bool],
        dim: Optional[bool],
        emphasis: Optional[bool],
        underline: Optional[bool],
        srikethrough: Optional[bool],
    ) -> Tuple[
        Optional[ANSIColor],
        Optional[ANSIColor],
        Optional[bool],
        Optional[bool],
        Optional[bool],
        Optional[bool],
        Optional[bool],
    ]:
        if self._color_stack:
            (
                prev_fg,
                prev_bg,
                prev_bold,
                prev_dim,
                prev_emphasis,
                prev_underline,
                prev_srikethrough,
            ) = self._color_stack[-1]

        if fg is None:
            fg = prev_fg if self._color_stack else None
        else:
            if fg not in IOConsole._fg.keys():
                raise ValueError(f"Invalid foreground color: {fg}")

        if bg is None:
            bg = prev_bg if self._color_stack else None
        else:
            if bg not in IOConsole._bg.keys():
                raise ValueError(f"Invalid foreground color: {bg}")

        if bold is None:
            bold = prev_bold if self._color_stack else None

        if dim is None:
            dim = prev_dim if self._color_stack else None

        if emphasis is None:
            emphasis = prev_emphasis if self._color_stack else None

        if underline is None:
            underline = prev_underline if self._color_stack else None

        if srikethrough is None:
            srikethrough = prev_srikethrough if self._color_stack else None

        return fg, bg, bold, dim, emphasis, underline, srikethrough

    @contextmanager
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
    ) -> Iterator[None]:
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
        fg, bg, bold, dim, emphasis, underline, srikethrough = self._get_styles(
            fg, bg, bold, dim, emphasis, underline, srikethrough
        )
        self._set_style(fg, bg, bold, dim, emphasis, underline, srikethrough)

        # propagate the current style to the stack
        self._color_stack.append((fg, bg, bold, dim, emphasis, underline, srikethrough))

        yield

        # pop the current style from the stack
        self._color_stack.pop()

        # reset the styles
        print(IOConsole._reset, end="")
        # set color from the stack
        if self._color_stack:
            fg, bg, bold, dim, emphasis, underline, srikethrough = self._color_stack[-1]
            self._set_style(fg, bg, bold, dim, emphasis, underline, srikethrough)
