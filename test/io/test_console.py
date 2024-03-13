from unittest.mock import MagicMock, patch

from pydantic import BaseModel
import pytest

from autogen.io import IOConsole
from autogen.io.console import ConsoleMessage
from autogen.io.messages import StreamMessageWrapper


class TestConsoleIO:
    def setup_method(self) -> None:
        self.console_io = IOConsole()

    @patch("builtins.print")
    def test_print(self, mock_print: MagicMock) -> None:
        # calling the print method should call the mock of the builtin print function
        self.console_io.print("Hello, World!", flush=True)
        mock_print.assert_called_once_with("Hello, World!", end="\n", sep=" ", flush=True)

    @patch("builtins.input")
    def test_input(self, mock_input: MagicMock) -> None:
        # calling the input method should call the mock of the builtin input function
        mock_input.return_value = "Hello, World!"

        actual = self.console_io.input("Hi!")
        assert actual == "Hello, World!"
        mock_input.assert_called_once_with("Hi!")

    @pytest.mark.parametrize("prompt", ["", "Password: ", "Enter you password:"])
    def test_input_password(self, monkeypatch: pytest.MonkeyPatch, prompt: str) -> None:
        mock_getpass = MagicMock()
        mock_getpass.return_value = "123456"
        monkeypatch.setattr("getpass.getpass", mock_getpass)

        actual = self.console_io.input(prompt, password=True)
        assert actual == "123456"
        if prompt == "":
            mock_getpass.assert_called_once_with("Password: ")
        else:
            mock_getpass.assert_called_once_with(prompt)

    @patch("builtins.print")
    def test_output(self, mock_print: MagicMock) -> None:
        StreamMessageWrapper._type2cls.clear()

        @StreamMessageWrapper.register_message_type(message_type="my_message")
        class MyMessage(BaseModel):
            sender: str
            receiver: str
            message: str

            def to_console(self) -> str:
                return f"{self.sender} -> {self.receiver}: {self.message}"

        msg = MyMessage(sender="Alice", receiver="Bob", message="Hello, Bob!")
        self.console_io.output(msg)
        mock_print.assert_called_once_with("Alice -> Bob: Hello, Bob!")
