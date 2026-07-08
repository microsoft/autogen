# Differences from Python

## Publishing to a topic that an agent is also subscribed to

> [!NOTE]
> TLDR; Default behavior is identical.

When an agent publishes a message to a topic to which it also listens, the message will not be received by the agent that sent it. This is also the behavior in the Python runtime. However to support previous usage, in @Microsoft.AutoGen.Core.InProcessRuntime, you can set the @Microsoft.AutoGen.Core.InProcessRuntime.DeliverToSelf property to true in the TopicSubscription attribute to allow an agent to receive messages it sends.
