from re import sub
from typing import Any, Callable, ClassVar, Dict, Literal, Set, Tuple, Type, TypeVar, Union
from pydantic import BaseModel, Field, create_model, field_validator

BM_T = TypeVar("BM_T", bound=Type[BaseModel])


class StreamMessageWrapper(BaseModel):
    """A message for an input/output stream."""

    type: str = Field(..., description="The type of the message.")
    content: BaseModel = Field(..., description="The content of the message.")

    _type2cls: ClassVar[Dict[str, Tuple[Type[BaseModel], Type["StreamMessageWrapper"]]]] = {}
    _cls2type: ClassVar[Dict[Type[BaseModel], str]] = {}

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the message."""
        cls = self.__class__
        if cls == StreamMessageWrapper:
            raise TypeError("StreamMessage cannot be instantiated directly. Please use StreamMessage.create() instead.")
        super().__init__(*args, **kwargs)

    @classmethod
    def clear_registry(cls) -> None:
        """Clear the message type registry."""
        cls._type2cls.clear()
        cls._cls2type.clear()

    @classmethod
    def _create_model(cls, *, message_type: str, content_cls: BM_T) -> Type["StreamMessageWrapper"]:
        class_name = "StreamMessage" + sub(r"(_|-)+", " ", message_type).title().replace(" ", "")

        def type_validator(cls: StreamMessageWrapper, v: str) -> str:
            if v != message_type:
                raise ValueError(f"Invalid message type '{v}'")
            return v

        def content_validator(cls: StreamMessageWrapper, v: BaseModel) -> BaseModel:
            if not isinstance(v, cls._type2cls[message_type]):
                raise ValueError(f"Invalid content type '{type(v)}' for message type '{message_type}'")
            return v

        MyStreamMessageWrapper = create_model(
            class_name,
            type=(str, message_type),
            content=(content_cls, ...),
            __base__=StreamMessageWrapper,
            __validators__={
                "type_validator": field_validator("type")(type_validator),  # type: ignore[dict-item, arg-type]
                "content_validator": field_validator("content")(content_validator),  # type: ignore[dict-item, arg-type]
            },
        )

        return MyStreamMessageWrapper

    @classmethod
    def register_message_type(cls, message_type: str) -> Callable[[BM_T], BM_T]:
        """Register a message type with the message."""

        def _decorator(content_cls: BM_T) -> BM_T:
            if message_type in cls._type2cls:
                message_cls, _ = cls._type2cls[message_type]
                raise ValueError(f"Message type '{message_type}' is already registered to '{message_cls}'.")
            elif content_cls in cls._cls2type:
                raise ValueError(
                    f"Message class '{content_cls}' is already registered to '{cls._cls2type[content_cls]}'."
                )

            wrapper_cls = cls._create_model(message_type=message_type, content_cls=content_cls)

            cls._type2cls[message_type] = (content_cls, wrapper_cls)
            cls._cls2type[content_cls] = message_type

            return content_cls

        return _decorator

    @classmethod
    def get_registered_message_types(cls) -> Dict[str, Tuple[Type[BaseModel], Type["StreamMessageWrapper"]]]:
        """Get a registered message types."""
        return cls._type2cls.copy()

    @classmethod
    def model_validate_json(
        cls,
        json_data: Union[str, bytes, bytearray],
        *,
        strict: Union[bool, None] = None,
        context: Union[Dict[str, Any], None] = None,
    ) -> "StreamMessageWrapper":
        """Validate a JSON string and return a model."""
        # if cls is a superclass of StreamMessage, use the BaseModel model_validate_json method
        if cls != StreamMessageWrapper:
            return super().model_validate_json(json_data, strict=strict, context=context)

        class _StreamMessage(BaseModel):
            type: str = Field(..., description="The type of the message.")
            content: Dict[str, Any] = Field(..., description="The content of the message.")

        obj = _StreamMessage.model_validate_json(json_data, strict=strict, context=context)

        _, message_class_wrapper = cls._type2cls.get(obj.type, (None, None))

        if message_class_wrapper is None:
            raise ValueError(f"Message type '{obj.type}' is not registered.")

        return message_class_wrapper.model_validate_json(json_data, strict=strict, context=context)

    @classmethod
    def create(cls, content: BaseModel) -> "StreamMessageWrapper":
        """Create a message."""
        message_type = cls._cls2type.get(content.__class__, None)
        if message_type is None:
            raise ValueError(f"Message class '{content.__class__}' is not registered.")

        _, message_wrapper_cls = cls._type2cls[message_type]

        return message_wrapper_cls(content=content)
