// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageDelivery.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core;

internal sealed class MessageDelivery(MessageEnvelope message, Func<MessageEnvelope, CancellationToken, ValueTask> servicer, IResultSink<object?>? resultSink = null)
{
    public MessageEnvelope Message { get; } = message;
    public Func<MessageEnvelope, CancellationToken, ValueTask> Servicer { get; } = servicer;
    public IResultSink<object?>? ResultSink { get; } = resultSink;

    public ValueTask<object?> Future => this.ResultSink != null ? this.ResultSink.Future : ValueTask.FromResult((object?)null);

    public ValueTask InvokeAsync(CancellationToken cancellation)
    {
        return this.Servicer(this.Message, cancellation);
    }
}

internal sealed class MessageEnvelope
{
    public object Message { get; }
    public string MessageId { get; }
    public TopicId? Topic { get; private set; }
    public AgentId? Sender { get; private set; }
    public AgentId? Receiver { get; private set; }
    public CancellationToken Cancellation { get; }

    public MessageEnvelope(object message, string? messageId = null, CancellationToken cancellation = default)
    {
        this.Message = message;
        this.MessageId = messageId ?? Guid.NewGuid().ToString();
        this.Cancellation = cancellation;
    }

    public MessageEnvelope WithSender(AgentId? sender)
    {
        this.Sender = sender;
        return this;
    }

    public MessageDelivery ForSend(AgentId receiver, Func<MessageEnvelope, CancellationToken, ValueTask<object?>> servicer)
    {
        this.Receiver = receiver;

        ResultSink<object?> resultSink = new ResultSink<object?>();
        Func<MessageEnvelope, CancellationToken, ValueTask> boundServicer = async (envelope, cancellation) =>
        {
            object? result = await servicer(envelope, cancellation);
            resultSink.SetResult(result);
        };

        return new MessageDelivery(this, boundServicer, resultSink);
    }

    public MessageDelivery ForPublish(TopicId topic, Func<MessageEnvelope, CancellationToken, ValueTask> servicer)
    {
        this.Topic = topic;

        return new MessageDelivery(this, servicer);
    }
}
