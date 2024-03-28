import json
from typing import Any, Dict

from pydantic import BaseModel
import pytest

from autogen.persistence.store import Serializable, SerializableRegistry
from autogen.version import __version__ as version


class TestRegisterSerializable:
    @pytest.fixture(autouse=True)
    def setup(self):
        def clear_registry():
            names = [name for name in SerializableRegistry._registry.keys() if name.startswith("test_persistence.")]
            for name in names:
                del SerializableRegistry._registry[name]

        clear_registry()

        class A:
            def __init__(self, i: int, s: str) -> None:
                self.i = i
                self.s = s

            class Model(BaseModel):
                i: int
                s: str

            def to_model(self) -> BaseModel:
                return A.Model(i=self.i, s=self.s)

            @classmethod
            def get_model_class(cls) -> BaseModel:
                return A.Model

            @classmethod
            def from_model(cls, model: BaseModel) -> "A":
                data = model.model_dump()
                return cls(**data)

        self.A = A

        yield

        clear_registry()

    def test_protocol_not_implemented(self):
        with pytest.raises(
            ValueError, match="is not a subclass of 'Serializable'. Please implement the 'Serializable' protocol first."
        ):

            @SerializableRegistry.register("test_persistence.A")
            class A: ...

    def test_just_register(self):
        A = self.A

        SerializableRegistry.register("test_persistence.A")(A)

        assert A in SerializableRegistry._registry.values()
        assert "test_persistence.A" in SerializableRegistry._registry.keys()

    def test_registered_already(self):
        A = self.A
        SerializableRegistry.register("test_persistence.A")(A)

        with pytest.raises(ValueError, match="is already registered as a serializable."):
            SerializableRegistry.register()(A)

        class B(A): ...

        with pytest.raises(ValueError, match="Type name 'test_persistence.A' is already registered."):
            # old name with new class
            SerializableRegistry.register("test_persistence.A")(B)

    def test_simple_serialization(self):
        A = self.A

        org_a = A(i=7, s="Hello World from original")
        org_model = org_a.to_model()
        org_dump = org_model.model_dump()
        assert org_dump == {"i": 7, "s": "Hello World from original"}

        SerializableRegistry.register("test_persistence.A")(A)

        a = A(i=4, s="Hello World")
        model = a.to_model()

        assert model.type == "test_persistence.A"
        assert model.version == version
        assert isinstance(model.data, BaseModel)
        assert model.data.i == 4
        assert model.data.s == "Hello World"

        actual = model.model_dump()
        expected = {"type": "test_persistence.A", "version": "0.2.20", "data": {"i": 4, "s": "Hello World"}}
        assert actual == expected

        decoded_A = SerializableRegistry.from_model(model)

        print(f"{decoded_A=}")
