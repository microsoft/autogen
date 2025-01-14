# Differences from Python

## Agents Self-Interact

When an agent sends a message of a type to which it also listens:

```csharp
[TopicSubscription("default")]
public class MyAgent(
    IAgentWorker worker,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry
    ) :
      Agent(worker, typeRegistry),
      IHandle<Message>
{
  async Task SomeInternalFunctionAsync()
  {
    Message m;

    // ...

    await this.PublishMessageAsync(m);
  }

  public async Task Handle(Message message)
  {
    // will receive messages sent by SomeInternalFunctionAsync()
  }
}
```

Tracked by [#4998](https://github.com/microsoft/autogen/issues/4998)

## 'Local' Runtime is Multithreaded

Unlike the `single_threaded_runtime`, the InProcess (`local: true`) runtime for .NET is multi-threaded, so messages will process in arbitrary order across agents. This means that an agent may process messages sent after the termination request has been made unless checking for termination using the `IHostApplicationLifecycle` service.

## No equivalent to 'stop_when_idle()'

Agents need to request termination explicitly, as there is no meaningful 'idle' state.

## All message types need to be Protocol Buffers

See (linkto: defining-message-types.md) for instructions on defining messages

Tracked by [#4695](https://github.com/microsoft/autogen/issues/4695)