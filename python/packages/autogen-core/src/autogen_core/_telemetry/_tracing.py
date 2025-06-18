import contextlib
import os
from typing import Dict, Generic, Iterator, Optional

from opentelemetry.trace import NoOpTracerProvider, Span, SpanKind, TracerProvider, get_tracer_provider
from opentelemetry.util import types

from ._propagation import TelemetryMetadataContainer, get_telemetry_links
from ._tracing_config import Destination, ExtraAttributes, Operation, TracingConfig


class TraceHelper(Generic[Operation, Destination, ExtraAttributes]):
    """
    TraceHelper is a utility class to assist with tracing operations using OpenTelemetry.

    This class provides a context manager `trace_block` to create and manage spans for tracing operations,
    following semantic conventions and supporting nested spans through metadata contexts.

    """

    def __init__(
        self,
        tracer_provider: TracerProvider | None,
        instrumentation_builder_config: TracingConfig[Operation, Destination, ExtraAttributes],
    ) -> None:
        self.instrumentation_builder_config = instrumentation_builder_config

        disable_runtime_tracing = os.environ.get("AUTOGEN_DISABLE_RUNTIME_TRACING") == "true"
        if disable_runtime_tracing:
            self.tracer_provider: TracerProvider = NoOpTracerProvider()
            self.tracer = self.tracer_provider.get_tracer(f"autogen {instrumentation_builder_config.name}")
            return

        # Evaluate in order: first try tracer_provider param, then get_tracer_provider(), finally fallback to NoOp
        # This allows for nested tracing with a default tracer provided by the user
        self.tracer_provider = tracer_provider or get_tracer_provider() or NoOpTracerProvider()
        self.tracer = self.tracer_provider.get_tracer(f"autogen {instrumentation_builder_config.name}")

    @contextlib.contextmanager
    def trace_block(
        self,
        operation: Operation,
        destination: Destination,
        parent: Optional[TelemetryMetadataContainer],
        *,
        extraAttributes: ExtraAttributes | None = None,
        kind: Optional[SpanKind] = None,
        attributes: Optional[types.Attributes] = None,
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
            operation (MessagingOperation): The messaging operation being performed.
            destination (MessagingDestination): The messaging destination being used.
            parent Optional[TelemetryMetadataContainer]: The parent telemetry metadta context
            kind (SpanKind, optional): The kind of span. If not provided, it maps to PRODUCER or CONSUMER depending on the operation.
            extraAttributes (ExtraAttributes, optional): Additional defined attributes for the span. Defaults to None.
            attributes (Optional[types.Attributes], optional): Additional non-defined attributes for the span. Defaults to None.
            start_time (Optional[int], optional): The start time of the span. Defaults to None.
            record_exception (bool, optional): Whether to record exceptions. Defaults to True.
            set_status_on_exception (bool, optional): Whether to set the status on exception. Defaults to True.
            end_on_exit (bool, optional): Whether to end the span on exit. Defaults to True.

        Yields:
            Iterator[Span]: The span object.

        """
        span_name = self.instrumentation_builder_config.get_span_name(operation, destination)
        span_kind = kind or self.instrumentation_builder_config.get_span_kind(operation)
        # context = get_telemetry_context(parent) if parent else None
        context = None  # TODO: we may need to remove other code for using custom context.
        links = get_telemetry_links(parent) if parent else None
        attributes_with_defaults: Dict[str, types.AttributeValue] = {}
        for key, value in (attributes or {}).items():
            attributes_with_defaults[key] = value
        instrumentation_attributes = self.instrumentation_builder_config.build_attributes(
            operation, destination, extraAttributes
        )
        for key, value in instrumentation_attributes.items():
            attributes_with_defaults[key] = value
        with self.tracer.start_as_current_span(
            span_name,
            context,
            span_kind,
            attributes_with_defaults,
            links,
            start_time,
            record_exception,
            set_status_on_exception,
            end_on_exit,
        ) as span:
            yield span
