from __future__ import annotations

from typing_extensions import Self

import pytest
from autogen_core import Component
from autogen_core._component_config import ComponentLoader
from autogen_core.models._model_client import ChatCompletionClient
from autogen_test_utils import MyInnerComponent, MyOuterComponent
from pydantic import BaseModel


class MyConfig(BaseModel):
    info: str


class MyComponent(Component("custom", MyConfig)): # type: ignore
    def __init__(self, info: str):
        self.info = info

    def _to_config(self) -> MyConfig:
        return MyConfig(info=self.info)

    @classmethod
    def _from_config(cls, config: MyConfig) -> MyComponent:
        return cls(info=config.info)


def test_custom_component():
    comp = MyComponent("test")
    comp2 = MyComponent.load_component(comp.dump_component())
    assert comp.info == comp2.info
    assert comp.__class__ == comp2.__class__


def test_custom_component_generic_loader():
    comp = MyComponent("test")
    comp2 = ComponentLoader.load_component(comp.dump_component(), MyComponent)
    assert comp.info == comp2.info
    assert comp.__class__ == comp2.__class__


def test_custom_component_incorrect_class():
    comp = MyComponent("test")

    with pytest.raises(TypeError):
        _ = ComponentLoader.load_component(comp.dump_component(), str)


def test_nested_component_diff_module():
    inner_class = MyInnerComponent("inner")
    comp = MyOuterComponent("test", inner_class)
    dumped = comp.dump_component()
    comp2 = MyOuterComponent.load_component(dumped)
    assert comp.__class__ == comp2.__class__
    assert comp.outer_message == comp2.outer_message
    assert comp.inner_class.inner_message == comp2.inner_class.inner_message
    assert comp.inner_class.__class__ == comp2.inner_class.__class__


def test_cannot_import_locals():
    class InvalidModelClientConfig(BaseModel):
        info: str

    class MyInvalidModelClient(Component("model", InvalidModelClientConfig)):
        def __init__(self, info: str):
            self.info = info

        def _to_config(self) -> InvalidModelClientConfig:
            return InvalidModelClientConfig(info=self.info)

        @classmethod
        def _from_config(cls, config: InvalidModelClientConfig) -> Self:
            return cls(info=config.info)

    comp = MyInvalidModelClient("test")
    with pytest.raises(TypeError):
        # Fails due to the class not being importable
        ChatCompletionClient.load_component(comp.dump_component())


class InvalidModelClientConfig(BaseModel):
    info: str


class MyInvalidModelClient(Component("model", InvalidModelClientConfig)):
    def __init__(self, info: str):
        self.info = info

    def _to_config(self) -> InvalidModelClientConfig:
        return InvalidModelClientConfig(info=self.info)

    @classmethod
    def _from_config(cls, config: InvalidModelClientConfig) -> Self:
        return cls(info=config.info)


def test_type_error_on_creation():
    comp = MyInvalidModelClient("test")
    # Fails due to MyInvalidModelClient not being a
    with pytest.raises(TypeError):
        ChatCompletionClient.load_component(comp.dump_component())
