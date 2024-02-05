from unittest.mock import patch, MagicMock
import pytest

from autogen.io import IOConsole
from autogen.io.base import ansi_colors


class TestConsoleIO:
    def setup_method(self) -> None:
        self.console_io = IOConsole()

    @patch("builtins.print")
    def test_print(self, mock_print: MagicMock) -> None:
        # calling the print method should call the mock of the builtin print function
        self.console_io.print("Hello, World!", flush=True)
        mock_print.assert_called_once_with("Hello, World!", end="\n", flush=True)

    def test_print_debug(self) -> None:
        # calling the print method should call the builtin print function
        self.console_io.print("Hello, World!", flush=True)

    @patch("builtins.input")
    def test_input(self, mock_input: MagicMock) -> None:
        # calling the input method should call the mock of the builtin input function
        mock_input.return_value = "Hello, World!"

        actual = self.console_io.input()
        assert actual == "Hello, World!"
        mock_input.assert_called_once_with()

    def test_set_style_visual_simple(self) -> None:
        # awaiting the print method should call the builtin print function
        self.console_io.print("Hello, World!", flush=True)
        with self.console_io.set_style(fg="cyan"):
            self.console_io.print("Hello, World in cyan!", flush=True)
            with self.console_io.set_style(bg="yellow"):
                self.console_io.print("Hello, World in cyan on yellow!", flush=True)
        with self.console_io.set_style(fg="magenta"):
            self.console_io.print("Hello, World in magenta!", flush=True)
            with self.console_io.set_style(bg="yellow"):
                self.console_io.print("Hello, World in magenta on yellow!", flush=True)
                with self.console_io.set_style(bold=True):
                    self.console_io.print("Hello, World in magenta on yellow bold!", flush=True)
            self.console_io.print("Hello, World in cyan again!", flush=True)
        self.console_io.print("Hello, World again!", flush=True)

    def test_set_style_visual_combinations(self) -> None:
        for fg in ansi_colors:
            for bg in ansi_colors:
                with self.console_io.set_style(fg=fg, bg=bg):
                    self.console_io.print(f"{fg} on {bg}", flush=True, end="")
