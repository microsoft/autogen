from typing import Any, Callable, Dict, List, Literal, Optional, Protocol, Type, TypeVar, runtime_checkable

from pydantic import BaseModel, Field

from ..version import __version__ as version

T = TypeVar("T")
S = TypeVar("S", bound="Type[Serializable]")


class SerializableRegistry:
    _registry: Dict[str, "Type[Serializable]"] = {}

    @classmethod
    def register(cls, type_name: Optional[str] = None) -> Callable[[S], S]:
        def _inner_register(serializable_cls: S, type_name: Optional[str] = type_name) -> S:
            if type_name is None:
                type_name = f"{serializable_cls.__module__}.{serializable_cls.__qualname__}"

            if not issubclass(serializable_cls, Serializable):
                raise ValueError(
                    f"{serializable_cls} is not a subclass of 'Serializable'. Please implement the 'Serializable' protocol first."
                )

            if serializable_cls in cls._registry.values():
                raise ValueError(f"Class '{serializable_cls}' is already registered as a serializable.")
            if type_name in cls._registry.keys():
                raise ValueError(f"Type name '{type_name}' is already registered.")

            original_to_model = serializable_cls.to_model
            original_model_class = serializable_cls.get_model_class()
            original_from_model = serializable_cls.from_model

            class Wrapper(BaseModel):

                type: Literal[type_name] = type_name  # type: ignore[valid-type]
                version: str
                data: original_model_class  # type: ignore[valid-type]

            def to_model(self: Serializable) -> Wrapper:
                original_data = original_to_model(self)

                return Wrapper(version=version, data=original_data)

            def get_model_class() -> Type[Wrapper]:
                return Wrapper

            def from_model(model: Wrapper) -> Serializable:
                if model.type != type_name:
                    raise ValueError(f"Model type '{model.type}' does not match the expected type '{type_name}'.")

                return original_from_model(model=model.data)

            serializable_cls.to_model = to_model  # type: ignore[method-assign]
            serializable_cls.get_model_class = get_model_class  # type: ignore[method-assign]
            serializable_cls.from_model = from_model  # type: ignore[method-assign,assignment]

            cls._registry[type_name] = serializable_cls

            return serializable_cls

        return _inner_register

    @classmethod
    def from_model(cls, model: BaseModel) -> "Serializable":
        if not hasattr(model, "type"):
            raise ValueError("Model does not have a 'type' attribute.")

        type_name = model.type
        serializable_cls = cls._registry[type_name]

        return serializable_cls.from_model(model)


@runtime_checkable
class Serializable(Protocol):

    def to_model(self) -> BaseModel:
        """Convert the object to a BaseModel object.

        Returns:
            BaseModel: The BaseModel object.

        """
        ...  # pragma: no cover

    @classmethod
    def get_model_class(cls) -> Type[BaseModel]:
        """Get the model class of the object.

        Returns:
            Type[BaseModel]: The model class.

        """
        ...

    @classmethod
    def from_model(cls: Type[T], model: BaseModel) -> T:
        """Create an instance of the class from a BaseModel object.

        Args:
            model (BaseModel): The BaseModel object.

        Returns:
            T: The instance of the class.

        """
        ...
