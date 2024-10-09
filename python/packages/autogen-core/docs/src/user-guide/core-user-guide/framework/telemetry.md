# Open Telemetry

AutoGen has native support for [open telemetry](https://opentelemetry.io/). This allows you to collect telemetry data from your application and send it to a telemetry backend of your choosing.

These are the components that are currently instrumented:
- Runtime (Single Threaded Agent Runtime, Worker Agent Runtime)

## Instrumenting your application
To instrument your application, you will need an sdk and an exporter. You may already have these if your application is already instrumented with open telemetry.

## Clean instrumentation

If you do not have open telemetry set up in your application, you can follow these steps to instrument your application.

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
# for single threaded runtime
single_threaded_runtime = SingleThreadedAgentRuntime(tracer_provider=tracer_provider)
# or for worker runtime
worker_runtime = WorkerAgentRuntime(tracer_provider=tracer_provider)
```

And that's it! Your application is now instrumented with open telemetry. You can now view your telemetry data in your telemetry backend.

### Exisiting instrumentation

If you have open telemetry already set up in your application, you can pass the tracer provider to the runtime when creating it:
```python
from opentelemetry import trace

# Get the tracer provider from your application
tracer_provider = trace.get_tracer_provider()

# for single threaded runtime
single_threaded_runtime = SingleThreadedAgentRuntime(tracer_provider=tracer_provider)
# or for worker runtime
worker_runtime = WorkerAgentRuntime(tracer_provider=tracer_provider)
```
