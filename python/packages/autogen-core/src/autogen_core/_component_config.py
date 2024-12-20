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
    component_type: ComponentType
    """Logical type of the component."""
    version: int
    """Version of the component specification."""
    description: str | None
    """Description of the component."""

    config: dict[str, Any]
    """The schema validated config field is passed to a given class's implmentation of :py:meth:`autogen_core.ComponentConfigImpl._from_config` to create a new instance of the component class."""


def _type_to_provider_str(t: type) -> str:
    return f"{t.__module__}.{t.__qualname__}"


@runtime_checkable
class ComponentConfigImpl(Protocol[ConfigT]):
    # Ideally would be ClassVar[Type[ConfigT]], but this is disallowed https://github.com/python/typing/discussions/1424 (despite being valid in this context)
    config_schema: Type[ConfigT]
    component_type: ClassVar[ComponentType]

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

        output = loaded_model.provider.rsplit(".", maxsplit=1)
        if len(output) != 2:
            raise ValueError("Invalid")

        module_path, class_name = output
        module = importlib.import_module(module_path)
        component_class = cast(ComponentConfigImpl[BaseModel], module.__getattribute__(class_name))

        if not isinstance(component_class, ComponentConfigImpl):
            raise TypeError("Invalid component class")

        # We need to check the schema is valid
        if not hasattr(component_class, "config_schema"):
            raise AttributeError("config_schema not defined")

        if not hasattr(component_class, "component_type"):
            raise AttributeError("component_type not defined")

        schema = component_class.config_schema
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

    - :py:attr:`config_schema` - A Pydantic model class which represents the configuration of the component. This is also the type parameter of Component.
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
            config_schema = Config

            def __init__(self, value: str):
                self.value = value

            def _to_config(self) -> Config:
                return Config(value=self.value)

            @classmethod
            def _from_config(cls, config: Config) -> MyComponent:
                return cls(value=config.value)
    """

    required_class_vars = ["config_schema", "component_type"]

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)

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
        provider = _type_to_provider_str(self.__class__)

        if "<locals>" in provider:
            raise TypeError("Cannot dump component with local class")

        if not hasattr(self, "component_type"):
            raise AttributeError("component_type not defined")

        obj_config = self._to_config().model_dump()
        return ComponentModel(
            provider=provider,
            component_type=self.component_type,
            version=1,
            description=None,
            config=obj_config,
        )
