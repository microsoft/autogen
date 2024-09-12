# Open Telemetry

AGNext has native support for [open telemetry](https://opentelemetry.io/). This allows you to collect telemetry data from your application and send it to a telemetry backend of your choosing.

These are the components that are currently instrumented:
- Runtime (Single Threaded Agent Runtime, Worker Agent Runtime)

## Instrumenting your application
To instrument your application, you will need an sdk and an exporter. You may already have these if your application is already instrumented with open telemetry.

```bash
pip install opentelemetry-sdk
```

Depending on your open telemetry collector, you can use grpc or http to export your telemetry. 

```bash
# Pick one of the following

pip install opentelemetry-exporter-otlp-proto-http
pip install opentelemetry-exporter-otlp-proto-grpc
```

Next, we need to get a tracer provider:
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def configure_oltp_tracing(endpoint: str = None) -> trace.TracerProvider:
    # Configure Tracing
    tracer_provider = TracerProvider(resource=Resource({"service.name": "my-service"}))
    processor = BatchSpanProcessor(OTLPSpanExporter())
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)
    
    return tracer_provider
```

Now you can send the trace_provider when creating your runtime:
```python
single_threaded_runtime = SingleThreadedAgentRuntime(tracer_provider=provider)
worker_runtime = WorkerAgentRuntime(tracer_provider=provider)
```

And that's it! Your application is now instrumented with open telemetry. You can now view your telemetry data in your telemetry backend.
