from typing import Dict

from pydantic import BaseModel, Field
import pytest

from autogen.io.messages import StreamMessageWrapper


class TestMessages:
    class MyMessage(BaseModel):
        """A message for the low-level interface."""

        sender: str = Field(..., description="The sender of the message.")
        receiver: str = Field(..., description="The receiver of the message.")
        content: str = Field(..., description="The content of the message.")

    class MyFuncCall(BaseModel):
        """A message for the low-level interface."""

        name: str = Field(..., description="The name of the function.")
        parameters: Dict[str, str] = Field(..., description="The parameters of the function.")

    def setup_method(self) -> None:
        StreamMessageWrapper.clear_registry()

    def test_init(self) -> None:
        with pytest.raises(TypeError, match="StreamMessage cannot be instantiated directly."):
            StreamMessageWrapper(
                type="my_message", content=TestMessages.MyMessage(sender="me", receiver="you", content="hello")
            )

    def test_clear_registry(self) -> None:
        assert StreamMessageWrapper.get_registered_message_types() == {}
        StreamMessageWrapper.register_message_type(message_type="my_message")(TestMessages.MyMessage)
        registered_message_types = StreamMessageWrapper.get_registered_message_types()
        assert set(registered_message_types.keys()) == set(["my_message"])
        StreamMessageWrapper.clear_registry()
        assert StreamMessageWrapper.get_registered_message_types() == {}

    def test_create_model(self) -> None:
        StreamMessageWrapper.register_message_type(message_type="my_message")(TestMessages.MyMessage)
        model_cls = StreamMessageWrapper._create_model(message_type="my_message", content_cls=TestMessages.MyMessage)
        assert issubclass(model_cls, StreamMessageWrapper)
        assert model_cls.__name__ == "StreamMessageMyMessage"

        model = model_cls(content=TestMessages.MyMessage(sender="me", receiver="you", content="hello"))
        assert model.type == "my_message"
        assert model.content == TestMessages.MyMessage(sender="me", receiver="you", content="hello")

        json_dump = model.model_dump_json(indent=2)
        expected = '{\n  "type": "my_message",\n  "content": {\n    "sender": "me",\n    "receiver": "you",\n    "content": "hello"\n  }\n}'
        assert json_dump == expected

    def test_register_message_type(self) -> None:
        StreamMessageWrapper.register_message_type(message_type="my_message")(TestMessages.MyMessage)
        registered_message_types = StreamMessageWrapper.get_registered_message_types()
        assert set(registered_message_types.keys()) == set(["my_message"])
        message_cls, message_wrapper_cls = registered_message_types["my_message"]
        assert message_cls == TestMessages.MyMessage
        assert issubclass(message_wrapper_cls, StreamMessageWrapper)

        StreamMessageWrapper.register_message_type(message_type="my_func_call")(TestMessages.MyFuncCall)
        registered_message_types = StreamMessageWrapper.get_registered_message_types()
        assert set(registered_message_types.keys()) == set(["my_message", "my_func_call"])
        message_cls, message_wrapper_cls = registered_message_types["my_func_call"]
        assert message_cls == TestMessages.MyFuncCall
        assert issubclass(message_wrapper_cls, StreamMessageWrapper)

        with pytest.raises(
            ValueError,
            match="Message type 'my_message' is already registered to '<class 'test_messages.TestMessages.MyMessage'>'.",
        ):
            StreamMessageWrapper.register_message_type(message_type="my_message")(TestMessages.MyMessage)

    def test_model_dump(self) -> None:
        StreamMessageWrapper.register_message_type(message_type="my_message")(TestMessages.MyMessage)
        msg = TestMessages.MyMessage(sender="me", receiver="you", content="hello")

        wrapper = StreamMessageWrapper.create(msg)

        assert wrapper.model_dump() == {
            "type": "my_message",
            "content": {"sender": "me", "receiver": "you", "content": "hello"},
        }

    def test_model_dump_json(self) -> None:
        StreamMessageWrapper.register_message_type(message_type="my_message")(TestMessages.MyMessage)
        msg = TestMessages.MyMessage(sender="me", receiver="you", content="hello")

        wrapper = StreamMessageWrapper.create(msg)

        assert (
            wrapper.model_dump_json()
            == '{"type":"my_message","content":{"sender":"me","receiver":"you","content":"hello"}}'
        )

    def test_model_validate_json(self) -> None:
        StreamMessageWrapper.register_message_type(message_type="my_message")(TestMessages.MyMessage)
        msg = TestMessages.MyMessage(sender="me", receiver="you", content="hello")
        assert msg.model_dump() == {"sender": "me", "receiver": "you", "content": "hello"}
        assert msg.model_dump_json() == '{"sender":"me","receiver":"you","content":"hello"}'

        StreamMessageWrapper.register_message_type(message_type="my_func_call")(TestMessages.MyFuncCall)

        wrapped_message = StreamMessageWrapper.create(
            TestMessages.MyMessage(sender="me", receiver="you", content="hello")
        )

        message_json = wrapped_message.model_dump_json()
        assert message_json == '{"type":"my_message","content":{"sender":"me","receiver":"you","content":"hello"}}'

        actual = StreamMessageWrapper.model_validate_json(message_json)
        assert actual == wrapped_message

    def test_create(self) -> None:
        StreamMessageWrapper.register_message_type(message_type="my_message")(TestMessages.MyMessage)
        StreamMessageWrapper.register_message_type(message_type="my_func_call")(TestMessages.MyFuncCall)

        inner_msg = TestMessages.MyMessage(sender="me", receiver="you", content="hello")
        msg = StreamMessageWrapper.create(inner_msg)
        assert msg.content == inner_msg
        assert msg.type == "my_message"

        dump = msg.model_dump()
        assert dump == {"type": "my_message", "content": {"sender": "me", "receiver": "you", "content": "hello"}}

        json_dump = msg.model_dump_json()
        assert json_dump == '{"type":"my_message","content":{"sender":"me","receiver":"you","content":"hello"}}'
