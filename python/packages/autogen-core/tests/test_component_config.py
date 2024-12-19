from __future__ import annotations

import json

import pytest
from autogen_core import Component, ComponentLoader, ComponentModel
from autogen_core._component_config import _type_to_provider_str  # type: ignore
from autogen_core.models import ChatCompletionClient
from autogen_test_utils import MyInnerComponent, MyOuterComponent
from pydantic import BaseModel, ValidationError
from typing_extensions import Self


class MyConfig(BaseModel):
    info: str


class MyComponent(Component[MyConfig]):
    config_schema = MyConfig
    component_type = "custom"

    def __init__(self, info: str) -> None:
        self.info = info

    def _to_config(self) -> MyConfig:
        return MyConfig(info=self.info)

    @classmethod
    def _from_config(cls, config: MyConfig) -> MyComponent:
        return cls(info=config.info)


def test_custom_component() -> None:
    comp = MyComponent("test")
    comp2 = MyComponent.load_component(comp.dump_component())
    assert comp.info == comp2.info
    assert comp.__class__ == comp2.__class__


def test_custom_component_generic_loader() -> None:
    comp = MyComponent("test")
    comp2 = ComponentLoader.load_component(comp.dump_component(), MyComponent)
    assert comp.info == comp2.info
    assert comp.__class__ == comp2.__class__


def test_custom_component_json() -> None:
    comp = MyComponent("test")
    json_str = comp.dump_component().model_dump_json()
    comp2 = MyComponent.load_component(json.loads(json_str))
    assert comp.info == comp2.info
    assert comp.__class__ == comp2.__class__


def test_custom_component_generic_loader_json() -> None:
    comp = MyComponent("test")
    json_str = comp.dump_component().model_dump_json()
    comp2 = ComponentLoader.load_component(json.loads(json_str), MyComponent)
    assert comp.info == comp2.info
    assert comp.__class__ == comp2.__class__


def test_custom_component_incorrect_class() -> None:
    comp = MyComponent("test")

    with pytest.raises(TypeError):
        _ = ComponentLoader.load_component(comp.dump_component(), str)


def test_nested_component_diff_module() -> None:
    inner_class = MyInnerComponent("inner")
    comp = MyOuterComponent("test", inner_class)
    dumped = comp.dump_component()
    comp2 = MyOuterComponent.load_component(dumped)
    assert comp.__class__ == comp2.__class__
    assert comp.outer_message == comp2.outer_message
    assert comp.inner_class.inner_message == comp2.inner_class.inner_message
    assert comp.inner_class.__class__ == comp2.inner_class.__class__


def test_nested_component_diff_module_json() -> None:
    inner_class = MyInnerComponent("inner")
    comp = MyOuterComponent("test", inner_class)
    dumped = comp.dump_component()
    json_str = dumped.model_dump_json()
    comp2 = MyOuterComponent.load_component(json.loads(json_str))
    assert comp.__class__ == comp2.__class__
    assert comp.outer_message == comp2.outer_message
    assert comp.inner_class.inner_message == comp2.inner_class.inner_message
    assert comp.inner_class.__class__ == comp2.inner_class.__class__


def test_cannot_import_locals() -> None:
    class InvalidModelClientConfig(BaseModel):
        info: str

    class MyInvalidModelClient(Component[InvalidModelClientConfig]):
        config_schema = InvalidModelClientConfig
        component_type = "model"

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


class MyInvalidModelClient(Component[InvalidModelClientConfig]):
    config_schema = InvalidModelClientConfig
    component_type = "model"

    def __init__(self, info: str) -> None:
        self.info = info

    def _to_config(self) -> InvalidModelClientConfig:
        return InvalidModelClientConfig(info=self.info)

    @classmethod
    def _from_config(cls, config: InvalidModelClientConfig) -> Self:
        return cls(info=config.info)


def test_type_error_on_creation() -> None:
    comp = MyInvalidModelClient("test")
    # Fails due to MyInvalidModelClient not being a model client
    with pytest.raises(TypeError):
        ChatCompletionClient.load_component(comp.dump_component())


with pytest.warns(UserWarning):

    class MyInvalidMissingAttrs(Component[InvalidModelClientConfig]):
        def __init__(self, info: str):
            self.info = info

        def _to_config(self) -> InvalidModelClientConfig:
            return InvalidModelClientConfig(info=self.info)

        @classmethod
        def _from_config(cls, config: InvalidModelClientConfig) -> Self:
            return cls(info=config.info)


def test_fails_to_save_on_missing_attributes() -> None:
    comp = MyInvalidMissingAttrs("test")  # type: ignore
    with pytest.raises(AttributeError):
        comp.dump_component()


def test_schema_validation_fails_on_bad_config() -> None:
    class OtherConfig(BaseModel):
        other: str

    config = OtherConfig(other="test").model_dump()
    model = ComponentModel(
        provider=_type_to_provider_str(MyComponent),
        component_type=MyComponent.component_type,
        version=1,
        description=None,
        config=config,
    )
    with pytest.raises(ValidationError):
        _ = MyComponent.load_component(model)
