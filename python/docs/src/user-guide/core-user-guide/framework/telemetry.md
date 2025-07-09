# Open Telemetry

AutoGen has native support for [open telemetry](https://opentelemetry.io/). This allows you to collect telemetry data from your application and send it to a telemetry backend of your choosing.

These are the components that are currently instrumented:

- Runtime ({py:class}`~autogen_core.SingleThreadedAgentRuntime` and {py:class}`~autogen_ext.runtimes.grpc.GrpcWorkerAgentRuntime`).
- Tool ({py:class}`~autogen_core.tools.BaseTool`) with the `execute_tool` span in [GenAI semantic convention for tools](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/#execute-tool-span).
- AgentChat Agents ({py:class}`~autogen_core.agents.BaseChatAgent`) with the `create_agent` and `invoke_agent` spans in [GenAI semantic convention for agents](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/#create-agent-span).

```{note}
To disable the agent runtime telemetry, you can set the `trace_provider` to
`opentelemetry.trace.NoOpTraceProvider` in the runtime constructor.

Additionally, you can set the environment variable `AUTOGEN_DISABLE_RUNTIME_TRACING` to `true` to disable the agent runtime telemetry if you don't have access to the runtime constructor. For example, if you are using `ComponentConfig`.
```

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
worker_runtime = GrpcWorkerAgentRuntime(tracer_provider=tracer_provider)
```

And that's it! Your application is now instrumented with open telemetry. You can now view your telemetry data in your telemetry backend.

### Existing instrumentation

If you have open telemetry already set up in your application, you can pass the tracer provider to the runtime when creating it:

```python
from opentelemetry import trace

# Get the tracer provider from your application
tracer_provider = trace.get_tracer_provider()

# for single threaded runtime
single_threaded_runtime = SingleThreadedAgentRuntime(tracer_provider=tracer_provider)
# or for worker runtime
worker_runtime = GrpcWorkerAgentRuntime(tracer_provider=tracer_provider)
```

### Examples

See [Tracing and Observability](../../agentchat-user-guide/tracing.ipynb)
for a complete example of how to set up open telemetry with AutoGen.
