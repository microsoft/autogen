from typing import List, Sequence

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult


class TestExporter(SpanExporter):
    def __init__(self) -> None:
        self.exported_spans: List[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.exported_spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def clear(self) -> None:
        """Clears the list of exported spans."""
        self.exported_spans.clear()

    def get_exported_spans(self) -> List[ReadableSpan]:
        """Returns the list of exported spans."""
        return self.exported_spans


def get_test_tracer_provider(exporter: TestExporter) -> TracerProvider:
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    return tracer_provider
