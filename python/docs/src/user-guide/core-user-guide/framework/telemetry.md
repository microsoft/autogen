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

Set up your Langfuse API keys. You can get these keys by signing up for a free [Langfuse Cloud](https://cloud.langfuse.com/) account or by [self-hosting Langfuse](https://langfuse.com/self-hosting).

```bash
pip install langfuse openlit "autogen-agentchat" "autogen-ext[openai]" -U
```

```python
import os

# Get keys for your project from the project settings page: https://cloud.langfuse.com
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..." 
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..." 
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com" # 🇪🇺 EU region
# os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com" # 🇺🇸 US region

# Your openai key
os.environ["OPENAI_API_KEY"] = "sk-proj-..."
```

With the environment variables set, we can now initialize the Langfuse client. `get_client()` initializes the Langfuse client using the credentials provided in the environment variables.

```python
from langfuse import Langfuse
 
# Filter out Autogen OpenTelemetry spans
langfuse = Langfuse(
    blocked_instrumentation_scopes=["autogen SingleThreadedAgentRuntime"]
)
 
# Verify connection
if langfuse.auth_check():
    print("Langfuse client is authenticated and ready!")
else:
    print("Authentication failed. Please check your credentials and host.")
```

Initialize OpenLit to start capturing OpenTelemetry traces.

```python
import openlit
 
# Initialize OpenLIT instrumentation. The disable_batch flag is set to true to process traces immediately.
openlit.init(tracer=langfuse._otel_tracer, disable_batch=True)
```

We'll create a simple AutoGen application where an Assistant agent answers a user's question.


```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o")
agent = AssistantAgent("assistant", model_client=model_client)
print(await agent.run(task="Say 'Hello World!'"))
await model_client.close()
```

_**Note:** Please refer to the [Langfuse documentation](https://langfuse.com/docs/integrations/autogen#interoperability-with-the-python-sdk) for guidance on how to add additional tracing attributes such as session_id and user_id, or how to modify trace inputs and outputs._

After running the agent above, you can log in to your Langfuse dashboard and view the traces generated by your AutoGen application. Here is an example screenshot of a trace in Langfuse:

![Langfuse Trace](https://langfuse.com/images/cookbook/integration-autogen/autogen-example-trace.png)

You can also view the public trace here: [Langfuse Trace Example](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/df850ab499107d4348584cf5933baabd?timestamp=2025-02-04T16%3A55%3A51.660Z&observation=286c648acb0105c2)

