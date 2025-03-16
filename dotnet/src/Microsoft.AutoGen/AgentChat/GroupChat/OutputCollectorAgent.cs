// Copyright (c) Microsoft Corporation. All rights reserved.
// OutputCollectorAgent.cs

using System.Diagnostics;
using Microsoft.AutoGen.AgentChat.GroupChat;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.AgentChat.Abstractions;

internal interface IOutputCollectionSink
{
    public void CollectMessage(AgentMessage message);
    public void Terminate(StopMessage message);
}

internal sealed class OutputSink : IOutputCollectionSink
{
    public sealed class SinkFrame
    {
        public StopMessage? Termination { get; set; }
        public List<AgentMessage> Messages { get; } = new();

        public bool IsTerminal => this.Termination != null;
    }

    private readonly object sync = new();
    private SemaphoreSlim semapohre = new SemaphoreSlim(0, 1);

    private SinkFrame? receivingSinkFrame;

    private void RunSynchronized(Action<SinkFrame> frameAction)
    {
        // Make sure we do not overlap with Terminate
        lock (this.sync)
        {
            if (this.receivingSinkFrame == null)
            {
                this.receivingSinkFrame = new SinkFrame();
            }

            frameAction(this.receivingSinkFrame);
        }

        // TODO: Replace the Semaphore with a TaskSource approach
        try
        {
            semapohre.Release();
        }
        catch (SemaphoreFullException) { }
    }

    public void CollectMessage(AgentMessage message)
    {
        this.RunSynchronized(
            frame =>
            {
                frame.Messages.Add(message);
            });
    }

    public void Terminate(StopMessage message)
    {
        this.RunSynchronized(
            frame =>
            {
                frame.Termination = message;
            });
    }

    public async Task<SinkFrame> WaitForDataAsync(CancellationToken cancellation)
    {
        while (true)
        {
            SinkFrame? lastFrame;
            lock (this.sync)
            {
                lastFrame = Interlocked.Exchange(ref this.receivingSinkFrame, null);

                if (lastFrame != null)
                {
                    return lastFrame;
                }
            }

            await this.semapohre.WaitAsync(cancellation);
        }
    }

    internal void Reset()
    {
        lock (this.sync)
        {
            this.receivingSinkFrame = null;
        }
    }
}

// TODO: Abstract the core logic of this out into the equivalent of ClosureAgent, because that seems like a
// useful facility to have in Core
internal sealed class OutputCollectorAgent : BaseAgent,
                                             IHandle<GroupChatStart>,
                                             IHandle<GroupChatMessage>,
                                             IHandle<GroupChatTermination>
{
    private IOutputCollectionSink Sink { get; }

    public OutputCollectorAgent(AgentInstantiationContext ctx, IOutputCollectionSink sink, ILogger<OutputCollectorAgent>? logger = null) : base(ctx.Id, ctx.Runtime, string.Empty, logger)
    {
        this.Sink = sink;
    }

    private void ForwardMessageInternal(ChatMessage message, CancellationToken cancel = default)
    {
        if (!cancel.IsCancellationRequested)
        {
            this.Sink.CollectMessage(message);
        }
    }

    public ValueTask HandleAsync(GroupChatStart item, MessageContext context)
    {
        item.Messages?.ForEach(item => this.ForwardMessageInternal(item, context.CancellationToken));

        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(GroupChatMessage item, MessageContext context)
    {
        Debug.Assert(item.Message is ChatMessage, "We should never receive internal messages into the output queue?");
        if (item.Message is ChatMessage chatMessage)
        {
            this.ForwardMessageInternal(chatMessage, context.CancellationToken);
        }

        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(GroupChatTermination item, MessageContext context)
    {
        this.Sink.Terminate(item.Message);

        return ValueTask.CompletedTask;
    }
}
