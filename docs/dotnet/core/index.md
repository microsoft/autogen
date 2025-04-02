# AutoGen Core

AutoGen Core for .NET follows the same concepts and conventions of its Python counterpart. In fact, in order to understand the concepts in the .NET version, we recommend reading the [Python documentation](https://microsoft.github.io/autogen/stable/) first. Unless otherwise stated, the concepts in the Python version map to .NET.

Any important differences between the language versions are documented in the [Differences from Python](./differences-from-python.md) section. For things that only affect a given language, such as dependency injection or host builder patterns, these will not be specified in the differences document.

## Getting Started

You can obtain the SDK as a nuget package or by cloning the repository. The SDK is available on [NuGet](https://www.nuget.org/packages/Microsoft.AutoGen).
Minimally you will need the following:

```bash
dotnet add package Microsoft.AutoGen.Contracts
dotnet add package Microsoft.AutoGen.Core
```

See [Installation](./installation.md) for more detailed notes on installing all the related packages. 

You can quickly get started by looking at the samples in the [samples](https://github.com/microsoft/autogen/tree/main/dotnet/samples) directory of the repository.

### Creating an Agent

To create an agent, you can inherit from BaseAgent and implement event handlers for the events you care about. Here is a minimal example demonstrating how to inherit from BaseAgent and implement an event handler:

```csharp
public class MyAgent : BaseAgent, IHandle<MyMessage>
{
    // ...
    public async ValueTask HandleAsync(MyMessage item, MessageContext context)
    {
        // ...logic here...
    }
}
```

By overriding BaseAgent, you gain access to the runtime and logging utilities, and by implementing IHandle<T>, you can easily define event-handling methods for your custom messages.

### Running an Agent in an Application

To run your agent in an application, you can use the `AgentsAppBuilder` class. Here is an example of how to run an agent 'HelloAgent' in an application:

```csharp
AgentsAppBuilder appBuilder = new AgentsAppBuilder()
    .UseInProcessRuntime(deliverToSelf: true)
    .AddAgent<HelloAgent>("HelloAgent");

var app = await appBuilder.BuildAsync();

// start the app by publishing a message to the runtime
await app.PublishMessageAsync(new NewMessageReceived
{
    Message = "Hello from .NET"
}, new TopicId("HelloTopic"));

// Wait for shutdown
await app.WaitForShutdownAsync();
```

## .NET SDK Runtimes

The .NET SDK includes both an InMemory Single Process Runtime and a Remote, Distributed Runtime meant for running your agents in the cloud. The Distributed Runtime supports running agents in python and in .NET, allowing those agents to talk to one another. The distributed runtime uses Microsoft Orleans to provide resilience, persistence, and integration with messaging services such as Azure Event Hubs.  The xlang functionality requires that your agent's Messages are serializable as CloudEvents.  The messages are exchanged as CloudEvents over Grpc, and the runtime takes care of ensuring that the messages are delivered to the correct agents. 

To use the Distributed Runtime, you will need to add the following package to your project:

```bash
dotnet add package Microsoft.AutoGen.Core.Grpc
```

This is the package that runs in the application with your agent(s) and connects to the distributed system. 

To Run the backend/server side you need:

```bash
dotnet add package Microsoft.AutoGen.RuntimeGateway
dotnet add package Microsoft.AutoGen.AgentHost
```

You can run the backend on its own:

```bash
dotnet run --project Microsoft.AutoGen.AgentHost
```

or you can run iclude it inside your own application:

```csharp
using Microsoft.AutoGen.RuntimeGateway;
using Microsoft.AutoGen.AgentHost;
var autogenBackend = await Microsoft.AutoGen.RuntimeGateway.Grpc.Host.StartAsync(local: false, useGrpc: true).ConfigureAwait(false);
```

You can also install the runtime as a dotnet tool:

```
dotnet pack --no-build --configuration Release --output './output/release' -bl\n
dotnet tool install --add-source ./output/release Microsoft.AutoGen.AgentHost
# run the tool
# dotnet agenthost 
# or just...  
agenthost 
```

### Running Multiple Agents and the Runtime in separate processes with .NET Aspire

The [Hello.AppHost project](https://github.com/microsoft/autogen/blob/50d7587a4649504af3bb79ab928b2a3882a1a394/dotnet/samples/Hello/Hello.AppHost/Program.cs#L4) illustrates how to orchestrate a distributed system with multiple agents and the runtime in separate processes using .NET Aspire. It also points to a [python agent that illustrates how to run agents in different languages in the same distributed system](https://github.com/microsoft/autogen/blob/50d7587a4649504af3bb79ab928b2a3882a1a394/python/samples/core_xlang_hello_python_agent/README.md#L1).

```csharp
// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.Extensions.Hosting;

var builder = DistributedApplication.CreateBuilder(args);
var backend = builder.AddProject<Projects.Microsoft_AutoGen_AgentHost>("backend").WithExternalHttpEndpoints();
var client = builder.AddProject<Projects.HelloAgent>("HelloAgentsDotNET")
    .WithReference(backend)
    .WithEnvironment("AGENT_HOST", backend.GetEndpoint("https"))
    .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
    .WaitFor(backend);
// xlang is over http for now - in prod use TLS between containers
builder.AddPythonApp("HelloAgentsPython", "../../../../python/samples/core_xlang_hello_python_agent", "hello_python_agent.py", "../../.venv")
    .WithReference(backend)
    .WithEnvironment("AGENT_HOST", backend.GetEndpoint("http"))
    .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
    .WithEnvironment("GRPC_DNS_RESOLVER", "native")
    .WithOtlpExporter()
    .WaitFor(client);
using var app = builder.Build();
await app.StartAsync();
var url = backend.GetEndpoint("http").Url;
Console.WriteLine("Backend URL: " + url);
await app.WaitForShutdownAsync();
```

You can find more examples of how to use Aspire and XLang agents in the [Microsoft.AutoGen.Integration.Tests.AppHost](https://github.com/microsoft/autogen/blob/acd7e864300e24a3ee67a89a916436e8894bb143/dotnet/test/Microsoft.AutoGen.Integration.Tests.AppHosts/) directory. 

### Configuring Logging

The SDK uses the Microsoft.Extensions.Logging framework for logging. Here is an example appsettings.json file with some useful defaults:

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Warning",
      "Microsoft.Hosting.Lifetime": "Information",
      "Microsoft.AspNetCore": "Information",
      "Microsoft": "Information",
      "Microsoft.Orleans": "Warning",
      "Orleans.Runtime": "Error",
      "Grpc": "Information"
    }
  },
  "AllowedHosts": "*",
  "Kestrel": {
    "EndpointDefaults": {
      "Protocols": "Http2"
    }
  }
}
```

### Defining Message Types in Protocol Buffers

A convenient way to define common event or message types to be used in both python and .NET agents is to define your events. This is covered here: [Using Protocol Buffers to Define Message Types](./protobuf-message-types.md).
