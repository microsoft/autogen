# Differences from Python

## Publishing to a topic that an agent is also subscribed to

> [!NOTE]
> TLDR; Default behavior is identical.

When an agent publishes a message to a topic to which it also listens, the message will not be received by the agent that sent it. This is also the behavior in the Python runtime. However to support previous usage, in @Microsoft.AutoGen.Core.InProcessRuntime, you can set the @Microsoft.AutoGen.Core.InProcessRuntime.DeliverToSelf property to true in the TopicSubscription attribute to allow an agent to receive messages it sends.

| Behavior                                         | Python Agent                 | .NET Agent                              |
| ------------------------------------------------ | ---------------------------- | --------------------------------------- |
| Agent publishes to a topic it also subscribes to | Own message **not received** | Own message **not received by default** |
| Enable self-receiving                            | —                            | `DeliverToSelf = true` can enable it    |
| Runtime mentioned                                | Python runtime               | `InProcessRuntime`                      |


## Python vs .NET

The default topic delivery behavior is the same in both runtimes: an agent
does not receive a message that it publishes to a topic it is subscribed to.

The .NET `InProcessRuntime` additionally supports opting into self-delivery
by setting `DeliverToSelf` to `true` in the `TopicSubscription` attribute.

