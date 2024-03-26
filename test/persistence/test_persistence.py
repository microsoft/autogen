import json
from typing import Any, Dict

import pytest

from autogen.persistence.store import Serializable, SerializableRegistry
from autogen.version import __version__ as version


class TestRegisterSerializable:
    @pytest.fixture(autouse=True)
    def setup(self):
        class_names = ["A"]

        fqnames = [
            "test_persistence.TestPersistence.test_SerializableRegistry.register.<locals>.{class_name}"
            for class_name in class_names
        ]

        def clear_registry():
            for fqname in fqnames:
                if fqname in SerializableRegistry._registry:
                    del SerializableRegistry._registry[fqname]

        clear_registry()

        yield

        clear_registry()

    def test_protocol_not_implemented(self):
        with pytest.raises(
            ValueError, match="is not a subclass of 'Serializable'. Please implement the 'Serializable' protocol first."
        ):

            @SerializableRegistry.register()
            class A: ...  # pragma: no cover

    def test_protocol_implemented(self):
        @SerializableRegistry.register()
        class A:
            def to_json(self) -> str: ...  # pragma: no cover

            def from_dict(cls, data: Dict[str, Any]) -> "Serializable": ...  # pragma: no cover

    def test_register(self):
        @SerializableRegistry.register()
        class A:
            def to_json(self) -> str: ...  # pragma: no cover
            def from_dict(cls, data: Dict[str, Any]) -> "Serializable": ...

        assert A in SerializableRegistry._registry.values()
        assert f"{A.__module__}.{A.__qualname__}" in SerializableRegistry._registry.keys()

    def test_registered_already(self):
        @SerializableRegistry.register()
        class A:
            def to_json(self) -> str: ...  # pragma: no cover
            def from_dict(cls, data: Dict[str, Any]) -> "Serializable": ...

        with pytest.raises(ValueError, match="is already registered as a serializable."):
            SerializableRegistry.register()(A)

        class B(A): ...  # pragma: no cover

        with pytest.raises(ValueError, match="Type name "):
            # old name with new class
            SerializableRegistry.register(f"{A.__module__}.{A.__qualname__}")(B)

    def test_simple_serialization(self):
        @SerializableRegistry.register()
        class A:
            def __init__(self, x: int):
                self.x = x

            def to_json(self) -> str:
                return json.dumps({"x": self.x})

            def from_dict(cls, data: Dict[str, Any]) -> "Serializable":
                return cls(json.loads(data))

        actual = A(4).to_json()
        expected = f'{{"type":"{A.__module__}.{A.__qualname__}","version":"{version}","data":{{"x":4}}}}'
        assert actual == expected

    # def test_SerializableRegistry.register(self):

    #     @SerializableRegistry.register()
    #     class A():
    #         def __init__(self, x: int):
    #             self.x = x

    #         def to_json(self) -> str:
    #             return json.dumps(self.x)

    #         # def to_dict(self) -> Dict[str, Any]:
    #         #     return dict(x=self.x)

    #     assert not hasattr(A, "something_random")
    #     print(f"{A.__dict__=}")
    #     assert hasattr(A, "_serialize"), f"{vars(A)=}"
    #     assert A._serialize is not None
    #     print(f"{A(x=3)._serialize()=}")

    #     # A = SerializableRegistry.register(A)

    #     # assert A in SERIALIZABLE_REGISTRY.values()

    #     # assert hasattr(A, "serialize")
    #     # actual = A(4).serialize()
    #     # expected = f'{{"type":"test_persistence.A","version":"{version}","data":{{"x":4}}}}'

    #     # actual = A(4).to_dict()
    #     # expected = {"type": "test_persistence.A", "version": version, "data": {"x": 4}}
    #     # assert actual == expected
