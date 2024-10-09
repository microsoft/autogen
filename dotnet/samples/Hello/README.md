# AutoGen .NET Hello World Sample

This sample demonstrates how to create a simple .NET console application that listens for an event and then orchestrates a series of actions in response.

## Prerequisites

To run this sample, you'll need: [.NET 8.0](https://dotnet.microsoft.com/en-us/) or later.
Also recommended is the [GitHub CLI](https://cli.github.com/).

## Instructions to run the sample

```bash
# Clone the repository
gh repo clone microsoft/autogen
cd dotnet/samples/Hello
dotnet run
```

## Key Concepts

This sample illustrates how to create your own agent that inherits from a base agent and listens for an event. It also shows how to use the SDK's App Runtime locally to start the agent and send messages.

Flow Diagram:

```mermaid
graph TD;
    A[Main] --> |PublishEvent(NewMessage\("World"\))| B("Handle\(NewMessageReceived item\)")
    B --> |"PublishEvent\(Output\("***Hello, World***"\)\)"| C[ConsoleAgent]
    C --> D(WriteConsole\(\))
    B --> |"PublishEvent(ConversationClosed\("Goodbye"\))"| E(Handle\(ConversationClosed item\))
    E --> F[Shutdown]

```

### Writing Event Handlers

The heart of an autogen application are the event handlers. Agents select a ```TopicSubscription``` to listen for events on a specific topic. When an event is received, the agent's event handler is called with the event data.

```csharp
TopicSubscription("HelloAgents")]
public class HelloAgent(
    IAgentContext context,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : ConsoleAgent(
        context,
        typeRegistry),
        ISayHello,
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>
{
    public async Task Handle(NewMessageReceived item)
    {
        var response = await SayHello(item.Message).ConfigureAwait(false);
        var evt = new Output
        {
            Message = response
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt).ConfigureAwait(false);
        var goodbye = new ConversationClosed
        {
            UserId = this.AgentId.Key,
            UserMessage = "Goodbye"
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(goodbye).ConfigureAwait(false);
    }
```

### Inheritance and Composition

### Starting the Application Runtime

### Sending Messages