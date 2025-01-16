# Quick Start

Before diving into the core APIs, let’s start with a simple example of two agents that count down from 10 to 1.

We first define the agent classes and their respective procedures for handling messages. We create two agent classes: `Modifier` and `Checker`. The `Modifier` agent modifies a number that is given and the `Check` agent checks the value against a condition. We also define a pair of
messages in a .proto file which will be generated into the message types that will be passed
between the agents.

```proto
syntax = "proto3";

package HelloAgents;

option csharp_namespace = "Microsoft.Autogen.Samples.CountAgent.Protocol";

message CountMessage {
    int32 Content = 1;
}

message CountUpdate {
    int32 NewCount = 1;
}
```

We create two messages to ensure we have tick-tock behaviour between the agents; if we used a single type, then both agents would receive the other agents' message as well as self-sent messages. (Note: this is a behaviour difference from Python; Issue#4998)

In the project file, we add

```xml
<ItemGroup>
  <PackageReference Include="Grpc.Tools" PrivateAssets="All" />
</ItemGroup>

<ItemGroup>
  <Protobuf Include="messages.proto" GrpcServices="Client;Server" Link="messages.proto" />
</ItemGroup>
```

This will ensure the message classes are available for our agents to send/receive.

Now we will define the agents:

```csharp
[TopicSubscription("default")]
public class Modifier(
    IAgentWorker worker,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
    ModifyF modifyFunc
    ) :
        Agent(worker, typeRegistry),
        IHandle<CountMessage>
{
    public async Task Handle(CountMessage item)
    {
        // handling code
    }
}
```

The `TopicSubscription` attribute defines the set of topics the agents will listen to. Topics (see here) are useful for separaating different logical chains of agent communications.

The first two parameters to the constructor, `IAgentWorker` and `EventTypes` are automatically made available through dependency injection to the workers. (We do not allow direct construction of workers in Autogen.Core: see here for FAQ), and need to be passed on to the base class.

Other parameters are also made available through dependency injection (see here).

Agents register for messages by implementing the `IHandle<MessageType>` interface:

```csharp
    public async Task Handle(CountMessage item)
    {
            int newValue = modifyFunc(item.Content);
            Console.WriteLine($"{SEPARATOR_LINE}\nModifier:\nModified {item.Content} to {newValue}");

            CountUpdate updateMessage = new CountUpdate { NewCount = newValue };

            await this.PublishMessageAsync(updateMessage);
    }
```

The `Modifier` agent receives a `CountMessage` indicating the current count, modifies it using the injected `ModifyF modifyFunc`, and publishes the `CountUpdate` message.

The `Checker` agent is defines similarly:

```csharp
[TopicSubscription("default")]
public class Checker(
    IAgentWorker worker,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
    IHostApplicationLifetime hostApplicationLifetime,
    TerminationF runUntilFunc
    ) :
        Agent(worker, typeRegistry),
        IHandle<CountUpdate>
{
  public Task Handle(CountUpdate item)
  {
    if (!runUntilFunc(item.NewCount))
    {
        Console.WriteLine($"{SEPARATOR_LINE}\nChecker:\n{item.NewCount} passed the check, continue.");
        await this.PublishMessageAsync(new CountMessage { Content = item.NewCount });
    }
    else
    {
        Console.WriteLine($"{SEPARATOR_LINE}\nChecker:\n{item.NewCount} failed the check, stopping.");
        hostApplicationLifetime.StopApplication();
    }
  }
}
```

The `Checker` continues the count when `runUntilFunc` has not triggered by publishing a new `CountMessage` with the updated count; if termination is desired, it will request it by calling `hostApplicationLifetime.StopApplication()`.

You might have already noticed, the agents’ logic, whether it is using model or code executor, is completely decoupled from how messages are delivered. This is the core idea: the framework provides a communication infrastructure, and the agents are responsible for their own logic. We call the communication infrastructure an Agent Runtime.

Agent runtime is a key concept of this framework. Besides delivering messages, it also manages agents’ lifecycle. So the creation of agents are handled by the runtime.

The following code shows how to register and run the agents using the local (InProcess) runtime:

```csharp
// Define the counting logic
using ModifyF = System.Func<int, int>;
using TerminationF = System.Func<int, bool>;

ModifyF modifyFunc = (int x) => x - 1;
TerminationF runUntilFunc = (int x) =>
{
    return x <= 1;
};

// Register the services
WebApplicationBuilder? builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton(modifyFunc);
builder.Services.AddSingleton(runUntilFunc);

// Send the initial count to the agents app, running on the `local` runtime, and pass through the registered services via the application `builder`
var app = await AgentsApp.PublishMessageAsync("default", new CountMessage
{
    Content = 10
}, local: true, builder: builder).ConfigureAwait(false);

// Run until application shutdown
await app.WaitForShutdownAsync();
```