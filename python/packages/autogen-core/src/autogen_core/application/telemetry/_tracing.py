import contextlib
import logging
from dataclasses import dataclass
from typing import Dict, Iterator, List, Literal, Mapping, Optional, Sequence, Union

from opentelemetry.context import Context
from opentelemetry.propagate import extract
from opentelemetry.trace import Link, Span, SpanKind, Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.util import types

from ...base import AgentId, TopicId

NAMESPACE = "autogen"

logger = logging.getLogger("autogen_core")
event_logger = logging.getLogger("autogen_core.events")


@dataclass(kw_only=True)
class EnvelopeMetadata:
    """Metadata for an envelope."""

    traceparent: Optional[str] = None
    tracestate: Optional[str] = None


def _get_carrier_for_envelope_metadata(envelope_metadata: EnvelopeMetadata) -> Dict[str, str]:
    carrier: Dict[str, str] = {}
    if envelope_metadata.traceparent is not None:
        carrier["traceparent"] = envelope_metadata.traceparent
    if envelope_metadata.tracestate is not None:
        carrier["tracestate"] = envelope_metadata.tracestate
    return carrier


def get_telemetry_envelope_metadata() -> EnvelopeMetadata:
    """
    Retrieves the telemetry envelope metadata.

    Returns:
        EnvelopeMetadata: The envelope metadata containing the traceparent and tracestate.
    """
    carrier: Dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)
    return EnvelopeMetadata(
        traceparent=carrier.get("traceparent"),
        tracestate=carrier.get("tracestate"),
    )


def _get_carrier_for_remote_call_metadata(remote_call_metadata: Mapping[str, str]) -> Dict[str, str]:
    carrier: Dict[str, str] = {}
    traceparent = remote_call_metadata.get("traceparent")
    tracestate = remote_call_metadata.get("tracestate")
    if traceparent:
        carrier["traceparent"] = traceparent
    if tracestate:
        carrier["tracestate"] = tracestate
    return carrier


def get_telemetry_grpc_metadata(existingMetadata: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """
    Retrieves the telemetry gRPC metadata.

    Args:
        existingMetadata (Optional[Mapping[str, str]]): The existing metadata to include in the gRPC metadata.

    Returns:
        Mapping[str, str]: The gRPC metadata containing the traceparent and tracestate.
    """
    carrier: Dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)
    traceparent = carrier.get("traceparent")
    tracestate = carrier.get("tracestate")
    metadata: Dict[str, str] = {}
    if existingMetadata is not None:
        for key, value in existingMetadata.items():
            metadata[key] = value
    if traceparent is not None:
        metadata["traceparent"] = traceparent
    if tracestate is not None:
        metadata["tracestate"] = tracestate
    return metadata


TelemetryMetadataContainer = Optional[EnvelopeMetadata] | Mapping[str, str]


def _get_telemetry_context(metadata: TelemetryMetadataContainer) -> Context:
    """
    Retrieves the telemetry context from the given metadata.

    Args:
        metadata (Optional[EnvelopeMetadata]): The metadata containing the telemetry context.

    Returns:
        Context: The telemetry context extracted from the metadata, or an empty context if the metadata is None.
    """
    if metadata is None:
        return Context()
    elif isinstance(metadata, EnvelopeMetadata):
        return extract(_get_carrier_for_envelope_metadata(metadata))
    elif hasattr(metadata, "__getitem__"):
        return extract(_get_carrier_for_remote_call_metadata(metadata))
    else:
        raise ValueError(f"Unknown metadata type: {type(metadata)}")


MessagingDestination = Union[AgentId, TopicId, str, None]


# TODO: Once we figure out how the destinations are stringified, we can use that convention
# https://github.com/microsoft/agnext/issues/399
def _get_destination_str(destination: MessagingDestination) -> str:
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


MessagingOperation = Literal["create", "send", "publish", "receive", "intercept", "process", "ack"]


def _get_span_name(
    operation: MessagingOperation,
    destination: Optional[MessagingDestination],
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
    destination_str = _get_destination_str(destination)
    if destination_str:
        span_parts.append(destination_str)
    span_name = " ".join(span_parts)
    return f"{NAMESPACE} {span_name}"


def _get_span_kind(operation: MessagingOperation) -> SpanKind:
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


@contextlib.contextmanager
def trace_block(
    tracer: Tracer,
    operation: MessagingOperation,
    destination: MessagingDestination,
    parent: Optional[TelemetryMetadataContainer],
    *,
    kind: Optional[SpanKind] = None,
    attributes: Optional[types.Attributes] = None,
    links: Optional[Sequence[Link]] = None,
    start_time: Optional[int] = None,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
    end_on_exit: bool = True,
) -> Iterator[Span]:
    """
    Thin wrapper on top of start_as_current_span.
    1. It helps us follow semantic conventions
    2. It helps us get contexts from metadata so we can get nested spans

    Args:
        tracer (Tracer): The tracer to use for tracing.
        operation (MessagingOperation): The messaging operation being performed.
        destination (MessagingDestination): The messaging destination being used.
        parent Optional[TelemetryMetadataContainer]: The parent telemetry metadta context
        kind (SpanKind, optional): The kind of span. If not provided, it maps to PRODUCER or CONSUMER depending on the operation.
        attributes (Optional[types.Attributes], optional): Additional attributes for the span. Defaults to None.
        links (Optional[Sequence[Link]], optional): Links to other spans. Defaults to None.
        start_time (Optional[int], optional): The start time of the span. Defaults to None.
        record_exception (bool, optional): Whether to record exceptions. Defaults to True.
        set_status_on_exception (bool, optional): Whether to set the status on exception. Defaults to True.
        end_on_exit (bool, optional): Whether to end the span on exit. Defaults to True.

    Yields:
        Iterator[Span]: The span object.

    """
    span_name = _get_span_name(operation, destination)
    span_kind = kind or _get_span_kind(operation)
    context = _get_telemetry_context(parent) if parent else None
    with tracer.start_as_current_span(
        span_name,
        context,
        span_kind,
        attributes,
        links,
        start_time,
        record_exception,
        set_status_on_exception,
        end_on_exit,
    ) as span:
        yield span
