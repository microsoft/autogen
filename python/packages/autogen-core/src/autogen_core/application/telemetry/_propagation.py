from dataclasses import dataclass
from typing import Dict, Mapping, Optional

from opentelemetry.context import Context
from opentelemetry.propagate import extract
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


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


def get_telemetry_context(metadata: TelemetryMetadataContainer) -> Context:
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
