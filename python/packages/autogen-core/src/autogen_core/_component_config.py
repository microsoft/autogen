from __future__ import annotations

import importlib
import warnings
from typing import Any, ClassVar, Dict, Generic, Literal, Protocol, Type, cast, overload, runtime_checkable

from pydantic import BaseModel
from typing_extensions import Self, TypeVar

ComponentType = Literal["model", "agent", "tool", "termination", "token_provider"] | str
ConfigT = TypeVar("ConfigT", bound=BaseModel)

T = TypeVar("T", bound=BaseModel, covariant=True)


class ComponentModel(BaseModel):
    """Model class for a component. Contains all information required to instantiate a component."""

    provider: str
    """Describes how the component can be instantiated."""

    component_type: ComponentType | None = None
    """Logical type of the component. If missing, the component assumes the default type of the provider."""

    version: int | None = None
    """Version of the component specification. If missing, the component assumes whatever is the current version of the library used to load it. This is obviously dangerous and should be used for user authored ephmeral config. For all other configs version should be specified."""

    component_version: int | None = None
    """Version of the component. If missing, the component assumes the default version of the provider."""

    description: str | None = None
    """Description of the component."""

    config: dict[str, Any]
    """The schema validated config field is passed to a given class's implmentation of :py:meth:`autogen_core.ComponentConfigImpl._from_config` to create a new instance of the component class."""


def _type_to_provider_str(t: type) -> str:
    return f"{t.__module__}.{t.__qualname__}"


WELL_KNOWN_PROVIDERS = {
    "azure_openai_chat_completion_client": "autogen_ext.models.openai.AzureOpenAIChatCompletionClient",
    "AzureOpenAIChatCompletionClient": "autogen_ext.models.openai.AzureOpenAIChatCompletionClient",
    "openai_chat_completion_client": "autogen_ext.models.openai.OpenAIChatCompletionClient",
    "OpenAIChatCompletionClient": "autogen_ext.models.openai.OpenAIChatCompletionClient",
}


@runtime_checkable
class ComponentConfigImpl(Protocol[ConfigT]):
    # Ideally would be ClassVar[Type[ConfigT]], but this is disallowed https://github.com/python/typing/discussions/1424 (despite being valid in this context)
    component_config_schema: Type[ConfigT]
    """The Pydantic model class which represents the configuration of the component."""
    component_type: ClassVar[ComponentType]
    """The logical type of the component."""
    component_version: ClassVar[int] = 1
    """The version of the component, if schema incompatibilities are introduced this should be updated."""
    component_provider_override: ClassVar[str | None] = None
    """Override the provider string for the component. This should be used to prevent internal module names being a part of the module name."""

    """The two methods a class must implement to be a component.

    Args:
        Protocol (ConfigT): Type which derives from :py:class:`pydantic.BaseModel`.
    """

    def _to_config(self) -> ConfigT:
        """Dump the configuration that would be requite to create a new instance of a component matching the configuration of this instance.

        Returns:
            T: The configuration of the component.

        :meta public:
        """
        ...

    @classmethod
    def _from_config(cls, config: ConfigT) -> Self:
        """Create a new instance of the component from a configuration object.

        Args:
            config (T): The configuration object.

        Returns:
            Self: The new instance of the component.

        :meta public:
        """
        ...

    @classmethod
    def _from_config_past_version(cls, config: Dict[str, Any], version: int) -> Self:
        """Create a new instance of the component from a previous version of the configuration object.

        This is only called when the version of the configuration object is less than the current version, since in this case the schema is not known.

        Args:
            config (Dict[str, Any]): The configuration object.
            version (int): The version of the configuration object.

        Returns:
            Self: The new instance of the component.

        :meta public:
        """
        raise NotImplementedError()


ExpectedType = TypeVar("ExpectedType")


class ComponentLoader:
    @overload
    @classmethod
    def load_component(cls, model: ComponentModel | Dict[str, Any], expected: None = None) -> Self: ...

    @overload
    @classmethod
    def load_component(cls, model: ComponentModel | Dict[str, Any], expected: Type[ExpectedType]) -> ExpectedType: ...

    @classmethod
    def load_component(
        cls, model: ComponentModel | Dict[str, Any], expected: Type[ExpectedType] | None = None
    ) -> Self | ExpectedType:
        """Load a component from a model. Intended to be used with the return type of :py:meth:`autogen_core.ComponentConfig.dump_component`.

        Example:

            .. code-block:: python

                from autogen_core import ComponentModel
                from autogen_core.models import ChatCompletionClient

                component: ComponentModel = ...  # type: ignore

                model_client = ChatCompletionClient.load_component(component)

        Args:
            model (ComponentModel): The model to load the component from.

        Returns:
            Self: The loaded component.

        Args:
            model (ComponentModel): _description_
            expected (Type[ExpectedType] | None, optional): Explicit type only if used directly on ComponentLoader. Defaults to None.

        Raises:
            ValueError: If the provider string is invalid.
            TypeError: Provider is not a subclass of ComponentConfigImpl, or the expected type does not match.

        Returns:
            Self | ExpectedType: The loaded component.
        """

        # Use global and add further type checks

        if isinstance(model, dict):
            loaded_model = ComponentModel(**model)
        else:
            loaded_model = model

        # First, do a look up in well known providers
        if loaded_model.provider in WELL_KNOWN_PROVIDERS:
            loaded_model.provider = WELL_KNOWN_PROVIDERS[loaded_model.provider]

        output = loaded_model.provider.rsplit(".", maxsplit=1)
        if len(output) != 2:
            raise ValueError("Invalid")

        module_path, class_name = output
        module = importlib.import_module(module_path)
        component_class = cast(ComponentConfigImpl[BaseModel], module.__getattribute__(class_name))

        if not isinstance(component_class, ComponentConfigImpl):
            raise TypeError("Invalid component class")

        # We need to check the schema is valid
        if not hasattr(component_class, "component_config_schema"):
            raise AttributeError("component_config_schema not defined")

        if not hasattr(component_class, "component_type"):
            raise AttributeError("component_type not defined")

        loaded_config_version = loaded_model.component_version or component_class.component_version
        if loaded_config_version < component_class.component_version:
            try:
                instance = component_class._from_config_past_version(loaded_model.config, loaded_config_version)  # type: ignore
            except NotImplementedError as e:
                raise NotImplementedError(
                    f"Tried to load component {component_class} which is on version {component_class.component_version} with a config on version {loaded_config_version} but _from_config_past_version is not implemented"
                ) from e
        else:
            schema = component_class.component_config_schema
            validated_config = schema.model_validate(loaded_model.config)

            # We're allowed to use the private method here
            instance = component_class._from_config(validated_config)  # type: ignore

        if expected is None and not isinstance(instance, cls):
            raise TypeError("Expected type does not match")
        elif expected is None:
            return cast(Self, instance)
        elif not isinstance(instance, expected):
            raise TypeError("Expected type does not match")
        else:
            return cast(ExpectedType, instance)


class Component(ComponentConfigImpl[ConfigT], ComponentLoader, Generic[ConfigT]):
    """To create a component class, inherit from this class. Then implement two class variables:

    - :py:attr:`component_config_schema` - A Pydantic model class which represents the configuration of the component. This is also the type parameter of Component.
    - :py:attr:`component_type` - What is the logical type of the component.

    Example:

    .. code-block:: python

        from __future__ import annotations

        from pydantic import BaseModel
        from autogen_core import Component


        class Config(BaseModel):
            value: str


        class MyComponent(Component[Config]):
            component_type = "custom"
            component_config_schema = Config

            def __init__(self, value: str):
                self.value = value

            def _to_config(self) -> Config:
                return Config(value=self.value)

            @classmethod
            def _from_config(cls, config: Config) -> MyComponent:
                return cls(value=config.value)
    """

    required_class_vars = ["component_config_schema", "component_type"]

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)

        # TODO: validate provider is loadable
        for var in cls.required_class_vars:
            if not hasattr(cls, var):
                warnings.warn(
                    f"Class variable '{var}' must be defined in {cls.__name__} to be a valid component", stacklevel=2
                )

    def dump_component(self) -> ComponentModel:
        """Dump the component to a model that can be loaded back in.

        Raises:
            TypeError: If the component is a local class.

        Returns:
            ComponentModel: The model representing the component.
        """
        if self.component_provider_override is not None:
            provider = self.component_provider_override
        else:
            provider = _type_to_provider_str(self.__class__)
            # Warn if internal module name is used,
            if "._" in provider:
                warnings.warn(
                    "Internal module name used in provider string. This is not recommended and may cause issues in the future. Silence this warning by setting component_provider_override to this value.",
                    stacklevel=2,
                )

        if "<locals>" in provider:
            raise TypeError("Cannot dump component with local class")

        if not hasattr(self, "component_type"):
            raise AttributeError("component_type not defined")

        obj_config = self._to_config().model_dump(exclude_none=True)
        model = ComponentModel(
            provider=provider,
            component_type=self.component_type,
            version=self.component_version,
            component_version=self.component_version,
            description=None,
            config=obj_config,
        )
        return model

    @classmethod
    def _from_config_past_version(cls, config: Dict[str, Any], version: int) -> Self:
        raise NotImplementedError()
