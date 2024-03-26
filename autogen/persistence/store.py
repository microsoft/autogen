import json
from typing import Callable, List, Dict, Any, Optional, Protocol, Type, TypeVar, runtime_checkable

from ..version import __version__ as version

T = TypeVar("T")
S = TypeVar("S", bound=Type["Serializable"])


class SerializableRegistry:
    _registry: Dict[str, "Serializable"] = {}

    @classmethod
    def register(cls, type_name: Optional[str] = None) -> Callable[[S], S]:
        def _inner_register(serializable_cls: S, type_name=type_name) -> S:
            if type_name is None:
                type_name = f"{serializable_cls.__module__}.{serializable_cls.__qualname__}"

            if not issubclass(serializable_cls, Serializable):
                raise ValueError(
                    f"{serializable_cls} is not a subclass of 'Serializable'. Please implement the 'Serializable' protocol first."
                )

            if serializable_cls in cls._registry.values():
                raise ValueError(f"{serializable_cls} is already registered as a serializable.")
            if type_name in cls._registry.keys():
                raise ValueError(f"Type name {type_name} is already registered.")

            original_to_json = serializable_cls.to_json

            def to_json(self: "Serializable") -> str:
                def _to_dict() -> Dict[str, Any]:
                    json_data = original_to_json(self)
                    data = json.loads(json_data)
                    return dict(type=type_name, version=version, data=data)

                data = _to_dict()

                return json.dumps(data, separators=(",", ":"))

            serializable_cls.to_json = to_json

            cls._registry[type_name] = serializable_cls

            return serializable_cls

        return _inner_register


@runtime_checkable
class Serializable(Protocol):
    def to_json(self) -> str:
        """Convert the object to a dictionary.

        Returns:
            str: The JSON representation of the object.

        """
        ...  # pragma: no cover

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Serializable":
        """Create an instance of the class from a dictionary.

        Args:
            data (str): The JSON representation of the object.

        Returns:
            Serializable: The instance of the class.

        """
        ...  # pragma: no cover
