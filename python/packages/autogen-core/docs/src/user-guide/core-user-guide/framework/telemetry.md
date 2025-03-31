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

## Example using Langfuse as OpenTelemetry Backend

Set your [Langfuse](https://github.com/langfuse/langfuse) API keys and configure OpenTelemetry export settings to send traces to the Langfuse OpenTelemetry backend. Please refer to the [Langfuse OpenTelemetry Docs](https://langfuse.com/docs/opentelemetry/get-started) for more information on this endpoint `/api/public/otel` authentication.

```python
import os
import base64

# Get keys for your project from the project settings page https://cloud.langfuse.com
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..." 
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..." 
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com" # 🇪🇺 EU region
# os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com" # 🇺🇸 US region

LANGFUSE_AUTH = base64.b64encode(
    f"{os.environ.get('LANGFUSE_PUBLIC_KEY')}:{os.environ.get('LANGFUSE_SECRET_KEY')}".encode()
).decode()

os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = os.environ.get("LANGFUSE_HOST") + "/api/public/otel"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

# your openai key
os.environ["OPENAI_API_KEY"] = "sk-proj-..."
```

Configure `tracer_provider` and add a span processor to export traces to Langfuse. `OTLPSpanExporter()` uses the endpoint and headers from the environment variables.

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

trace_provider = TracerProvider()
trace_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))

# Sets the global default tracer provider
from opentelemetry import trace
trace.set_tracer_provider(trace_provider)

# Creates a tracer from the global tracer provider
tracer = trace.get_tracer(__name__)
```

Initialize OpenLit to start capturing OpenTelemetry traces.

```python
import openlit

# Initialize OpenLIT instrumentation. The disable_batch flag is set to true to process traces immediately.
openlit.init(tracer=tracer, disable_batch=True)
```

We'll create a simple AutoGen application where an Assistant agent answers a user's question.


```python
import autogen
from autogen import AssistantAgent, UserProxyAgent

llm_config = {"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}
assistant = AssistantAgent("assistant", llm_config=llm_config)

user_proxy = UserProxyAgent(
    "user_proxy", code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")}
)

# Start the chat
user_proxy.initiate_chat(
    assistant,
    message="What is Langfuse?",
)
```

Opentelemetry lets you attach a set of attributes to all spans by setting [`set_attribute`](https://opentelemetry.io/docs/languages/python/instrumentation/#add-attributes-to-a-span). This allows you to set properties like a Langfuse Session ID, to group traces into Langfuse Sessions or a User ID, to assign traces to a specific user. You can find a list of all supported attributes in the [here](/docs/opentelemetry/get-started#property-mapping).


```python
with tracer.start_as_current_span("AutoGen-Trace") as span:
    span.set_attribute("langfuse.user.id", "user-123")
    span.set_attribute("langfuse.session.id", "123456789")
    span.set_attribute("langfuse.tags", ["semantic-kernel", "demo"])
    span.set_attribute("langfuse.prompt.name", "test-1")

    # Start the chat
    user_proxy.initiate_chat(
        assistant,
        message="What is Langfuse?",
    )
```

After running the agent above, you can log in to your Langfuse dashboard and view the traces generated by your AutoGen application. Here is an example screenshot of a trace in Langfuse:

![Langfuse Trace](https://langfuse.com/images/cookbook/integration-autogen/autogen-example-trace.png)

You can also view the public trace here: [Langfuse Trace Example](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/df850ab499107d4348584cf5933baabd?timestamp=2025-02-04T16%3A55%3A51.660Z&observation=286c648acb0105c2)

