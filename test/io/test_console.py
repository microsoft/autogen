from unittest.mock import patch, MagicMock

from autogen.io import IOConsole


class TestConsoleIO:
    def setup_method(self) -> None:
        self.console_io = IOConsole()

    @patch("builtins.print")
    def test_print(self, mock_print: MagicMock) -> None:
        # calling the print method should call the mock of the builtin print function
        self.console_io.print("Hello, World!", flush=True)
        mock_print.assert_called_once_with("Hello, World!", end="\n", sep=" ", flush=True)

    def test_print_debug(self) -> None:
        # calling the print method should call the builtin print function
        self.console_io.print("Hello, World!", flush=True)

    @patch("builtins.input")
    def test_input(self, mock_input: MagicMock) -> None:
        # calling the input method should call the mock of the builtin input function
        mock_input.return_value = "Hello, World!"

        actual = self.console_io.input("Hi!")
        assert actual == "Hello, World!"
        mock_input.assert_called_once_with("Hi!")
