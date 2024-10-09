import logging
from abc import ABC, abstractmethod
from typing import Dict, Generic, List, Literal, TypedDict, TypeVar, Union

from opentelemetry.trace import SpanKind
from opentelemetry.util import types
from typing_extensions import NotRequired

from ...base import AgentId, TopicId
from ._constants import NAMESPACE

logger = logging.getLogger("autogen_core")
event_logger = logging.getLogger("autogen_core.events")

Operation = TypeVar("Operation", bound=str)
Destination = TypeVar("Destination")
ExtraAttributes = TypeVar("ExtraAttributes")


class TracingConfig(ABC, Generic[Operation, Destination, ExtraAttributes]):
    """
    A protocol that defines the configuration for instrumentation.

    This protocol specifies the required properties and methods that any
    instrumentation configuration class must implement. It includes a
    property to get the name of the module being instrumented and a method
    to build attributes for the instrumentation configuration.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns:
            The name of the module that is being instrumented.
        """
        ...

    @abstractmethod
    def build_attributes(
        self,
        operation: Operation,
        destination: Destination,
        extraAttributes: ExtraAttributes | None,
    ) -> Dict[str, types.AttributeValue]:
        """
        Builds the attributes for the instrumentation configuration.

        Returns:
            Dict[str, str]: The attributes for the instrumentation configuration.
        """
        ...

    @abstractmethod
    def get_span_name(
        self,
        operation: Operation,
        destination: Destination,
    ) -> str:
        """
        Returns the span name based on the given operation and destination.

        Parameters:
            operation (MessagingOperation): The messaging operation.
            destination (Optional[MessagingDestination]): The messaging destination.

        Returns:
            str: The span name.
        """
        ...

    @abstractmethod
    def get_span_kind(
        self,
        operation: Operation,
    ) -> SpanKind:
        """
        Determines the span kind based on the given messaging operation.

        Parameters:
            operation (MessagingOperation): The messaging operation.

        Returns:
            SpanKind: The span kind based on the messaging operation.
        """


class ExtraMessageRuntimeAttributes(TypedDict):
    message_size: NotRequired[int]
    message_type: NotRequired[str]


MessagingDestination = Union[AgentId, TopicId, str, None]
MessagingOperation = Literal["create", "send", "publish", "receive", "intercept", "process", "ack"]


class MessageRuntimeTracingConfig(
    TracingConfig[MessagingOperation, MessagingDestination, ExtraMessageRuntimeAttributes]
):
    """
    A class that defines the configuration for message runtime instrumentation.

    This class implements the TracingConfig protocol and provides
    the name of the module being instrumented and the attributes for the
    instrumentation configuration.
    """

    def __init__(self, runtime_name: str) -> None:
        self._runtime_name = runtime_name

    @property
    def name(self) -> str:
        return self._runtime_name

    def build_attributes(
        self,
        operation: MessagingOperation,
        destination: MessagingDestination,
        extraAttributes: ExtraMessageRuntimeAttributes | None,
    ) -> Dict[str, types.AttributeValue]:
        attrs: Dict[str, types.AttributeValue] = {
            "messaging.operation": self._get_operation_type(operation),
            "messaging.destination": self._get_destination_str(destination),
        }
        if extraAttributes:
            # TODO: Make this more pythonic?
            if "message_size" in extraAttributes:
                attrs["messaging.message.envelope.size"] = extraAttributes["message_size"]
            if "message_type" in extraAttributes:
                attrs["messaging.message.type"] = extraAttributes["message_type"]
        return attrs

    def get_span_name(
        self,
        operation: MessagingOperation,
        destination: MessagingDestination,
    ) -> str:
        """
        Returns the span name based on the given operation and destination.
        Semantic Conventions - https://opentelemetry.io/docs/specs/semconv/messaging/messaging-spans/#span-name

        Parameters:
            operation (MessagingOperation): The messaging operation.
            destination (Optional[MessagingDestination]): The messaging destination.

        Returns:
            str: The span name.
        """
        span_parts: List[str] = [operation]
        destination_str = self._get_destination_str(destination)
        if destination_str:
            span_parts.append(destination_str)
        span_name = " ".join(span_parts)
        return f"{NAMESPACE} {span_name}"

    def get_span_kind(
        self,
        operation: MessagingOperation,
    ) -> SpanKind:
        """
        Determines the span kind based on the given messaging operation.
        Semantic Conventions - https://opentelemetry.io/docs/specs/semconv/messaging/messaging-spans/#span-kind

        Parameters:
            operation (MessagingOperation): The messaging operation.

        Returns:
            SpanKind: The span kind based on the messaging operation.
        """
        if operation in ["create", "send", "publish"]:
            return SpanKind.PRODUCER
        elif operation in ["receive", "intercept", "process", "ack"]:
            return SpanKind.CONSUMER
        else:
            return SpanKind.CLIENT

    # TODO: Use stringified convention
    def _get_destination_str(self, destination: MessagingDestination) -> str:
        if isinstance(destination, AgentId):
            return f"{destination.type}.({destination.key})-A"
        elif isinstance(destination, TopicId):
            return f"{destination.type}.({destination.source})-T"
        elif isinstance(destination, str):
            return destination
        elif destination is None:
            return ""
        else:
            raise ValueError(f"Unknown destination type: {type(destination)}")

    def _get_operation_type(self, operation: MessagingOperation) -> str:
        if operation in ["send", "publish"]:
            return "publish"
        if operation in ["create"]:
            return "create"
        elif operation in ["receive", "intercept", "ack"]:
            return "receive"
        elif operation in ["process"]:
            return "process"
        else:
            return "Unknown"
