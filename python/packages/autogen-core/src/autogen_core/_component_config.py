from __future__ import annotations
import importlib
import types
from typing import Generic, Literal, Protocol, Type, cast, overload, runtime_checkable

from pydantic import BaseModel
from typing_extensions import Self, TypeVar


ComponentType = Literal["model", "agent", "tool", "termination", "token_provider"] | str
ConfigT = TypeVar("ConfigT", bound=BaseModel)

T = TypeVar("T", bound=BaseModel, covariant=True)

class ComponentModel(BaseModel):
    """Model class for a component. Contains all information required to instantiate a component."""

    provider: str
    """Describes how the component can be instantiated."""
    component_type: ComponentType
    """Logical type of the component."""
    version: int
    """Version of the component specification."""
    description: str | None
    """Description of the component."""

    config: BaseModel
    """The config field is passed to a given class's implmentation of :py:meth:`autogen_core.ComponentConfigImpl._from_config` to create a new instance of the component class."""


def _type_to_provider_str(t: type) -> str:
    return f"{t.__module__}.{t.__qualname__}"

@runtime_checkable
class ComponentConfigImpl(Protocol[ConfigT]):
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


ExpectedType = TypeVar("ExpectedType")
class ComponentLoader():

    @overload
    @classmethod
    def load_component(cls, model: ComponentModel, expected: None = None) -> Self:
        ...

    @overload
    @classmethod
    def load_component(cls, model: ComponentModel, expected: Type[ExpectedType]) -> ExpectedType:
        ...

    @classmethod
    def load_component(cls, model: ComponentModel, expected: Type[ExpectedType] | None = None) -> Self | ExpectedType:
        """Load a component from a model. Intended to be used with the return type of :py:meth:`autogen_core.ComponentConfig.dump_component`.

        Example:

            .. code-block:: python

                from autogen_core import ComponentModel
                from autogen_core.models import ChatCompletionClient

                component: ComponentModel = ... # type: ignore

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

        output = model.provider.rsplit(".", maxsplit=1)
        if len(output) != 2:
            raise ValueError("Invalid")

        module_path, class_name = output
        module = importlib.import_module(module_path)
        component_class = cast(ComponentConfigImpl[BaseModel], module.__getattribute__(class_name))

        if not isinstance(component_class, ComponentConfigImpl):
            raise TypeError("Invalid component class")

        # We're allowed to use the private method here
        instance = component_class._from_config(model.config) # type: ignore

        if expected is None and not isinstance(instance, cls):
            raise TypeError("Expected type does not match")
        elif expected is None:
            return cast(Self, instance)
        elif not isinstance(instance, expected):
            raise TypeError("Expected type does not match")
        else:
            return cast(ExpectedType, instance)


class ComponentConfig(ComponentConfigImpl[ConfigT], ComponentLoader, Generic[ConfigT]):
    _config_schema: Type[ConfigT]
    _component_type: ComponentType
    _description: str | None

    def dump_component(self) -> ComponentModel:
        """Dump the component to a model that can be loaded back in.

        Raises:
            TypeError: If the component is a local class.

        Returns:
            ComponentModel: The model representing the component.
        """
        provider = _type_to_provider_str(self.__class__)

        if "<locals>" in provider:
            raise TypeError("Cannot dump component with local class")

        return ComponentModel(
            provider=provider,
            component_type=self._component_type,
            version=1,
            description=self._description,
            config=self._to_config(),
        )

    @classmethod
    def component_config_schema(cls) -> Type[ConfigT]:
        """Get the configuration schema for the component.

        Returns:
            Type[ConfigT]: The configuration schema for the component.
        """
        return cls._config_schema

    @classmethod
    def component_type(cls) -> ComponentType:
        """Logical type of the component.

        Returns:
            ComponentType: The logical type of the component.
        """
        return cls._component_type


def Component(
    component_type: ComponentType, config_schema: type[T], description: str | None = None
) -> type[ComponentConfig[T]]:
    """This enables easy creation of Component classes. It provides a type to inherit from to provide the necessary methods to be a component.

    Example:

    .. code-block:: python

        from pydantic import BaseModel
        from autogen_core import Component

        class Config(BaseModel):
            value: str

        class MyComponent(Component("custom", Config)):
            def __init__(self, value: str):
                self.value = value

            def _to_config(self) -> Config:
                return Config(value=self.value)

            @classmethod
            def _from_config(cls, config: Config) -> MyComponent:
                return cls(value=config.value)


    Args:
        component_type (ComponentType): What is the logical type of the component.
        config_schema (type[T]): Pydantic model class which represents the configuration of the component.
        description (str | None, optional): Helpful description of the component. Defaults to None.

    Returns:
        type[ComponentConfig[T]]: A class to be directly inherited from.
    """
    return types.new_class(
        "Component",
        (ComponentConfig[T],),
        exec_body=lambda ns: ns.update(
            {"_config_schema": config_schema, "_component_type": component_type, "_description": description}
        ),
    )
