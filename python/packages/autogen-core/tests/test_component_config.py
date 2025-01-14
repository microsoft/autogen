from __future__ import annotations

import json
from typing import Any, Dict

import pytest
from autogen_core import Component, ComponentBase, ComponentLoader, ComponentModel
from autogen_core._component_config import _type_to_provider_str  # type: ignore
from autogen_core.models import ChatCompletionClient
from autogen_test_utils import MyInnerComponent, MyOuterComponent
from pydantic import BaseModel, ValidationError
from typing_extensions import Self


class MyConfig(BaseModel):
    info: str


class MyComponent(ComponentBase[MyConfig], Component[MyConfig]):
    component_config_schema = MyConfig
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

    class MyInvalidModelClient(ComponentBase[InvalidModelClientConfig], Component[InvalidModelClientConfig]):
        component_config_schema = InvalidModelClientConfig
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


class MyInvalidModelClient(ComponentBase[InvalidModelClientConfig], Component[InvalidModelClientConfig]):
    component_config_schema = InvalidModelClientConfig
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

    class MyInvalidMissingAttrs(ComponentBase[InvalidModelClientConfig], Component[InvalidModelClientConfig]):
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


def test_config_optional_values() -> None:
    config = {
        "provider": _type_to_provider_str(MyComponent),
        "config": {"info": "test"},
    }

    model = ComponentModel.model_validate(config)
    component = MyComponent.load_component(model)
    assert component.info == "test"
    assert component.__class__ == MyComponent


class ConfigProviderOverrided(ComponentBase[MyConfig], Component[MyConfig]):
    component_provider_override = "InvalidButStillOverridden"
    component_config_schema = MyConfig
    component_type = "custom"

    def __init__(self, info: str):
        self.info = info

    def _to_config(self) -> MyConfig:
        return MyConfig(info=self.info)

    @classmethod
    def _from_config(cls, config: MyConfig) -> Self:
        return cls(info=config.info)


def test_config_provider_override() -> None:
    comp = ConfigProviderOverrided("test")
    dumped = comp.dump_component()
    assert dumped.provider == "InvalidButStillOverridden"


class MyConfig2(BaseModel):
    info2: str


class ComponentNonOneVersion(ComponentBase[MyConfig2], Component[MyConfig2]):
    component_config_schema = MyConfig2
    component_version = 2
    component_type = "custom"

    def __init__(self, info: str):
        self.info = info

    def _to_config(self) -> MyConfig2:
        return MyConfig2(info2=self.info)

    @classmethod
    def _from_config(cls, config: MyConfig2) -> Self:
        return cls(info=config.info2)


class ComponentNonOneVersionWithUpgrade(ComponentBase[MyConfig2], Component[MyConfig2]):
    component_config_schema = MyConfig2
    component_version = 2
    component_type = "custom"

    def __init__(self, info: str):
        self.info = info

    def _to_config(self) -> MyConfig2:
        return MyConfig2(info2=self.info)

    @classmethod
    def _from_config(cls, config: MyConfig2) -> Self:
        return cls(info=config.info2)

    @classmethod
    def _from_config_past_version(cls, config: Dict[str, Any], version: int) -> Self:
        model = MyConfig.model_validate(config)
        return cls(info=model.info)


def test_component_version() -> None:
    comp = ComponentNonOneVersion("test")
    dumped = comp.dump_component()
    assert dumped.version == 2
    comp2 = ComponentNonOneVersion.load_component(dumped)
    assert comp.info == comp2.info
    assert comp.__class__ == comp2.__class__


def test_component_version_from_dict_non_existing_impl() -> None:
    config = {
        "provider": _type_to_provider_str(ComponentNonOneVersion),
        "config": {"info": "test"},
        "component_version": 1,
    }

    with pytest.raises(NotImplementedError):
        ComponentNonOneVersion.load_component(config)


def test_component_version_from_dict() -> None:
    config = {
        "provider": _type_to_provider_str(ComponentNonOneVersionWithUpgrade),
        "config": {"info": "test"},
        "component_version": 1,
    }

    comp = ComponentNonOneVersionWithUpgrade.load_component(config)
    assert comp.info == "test"
    assert comp.__class__ == ComponentNonOneVersionWithUpgrade
    assert comp.dump_component().version == 2
