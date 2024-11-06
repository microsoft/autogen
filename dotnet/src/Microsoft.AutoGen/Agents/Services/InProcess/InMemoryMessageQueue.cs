// Copyright (c) Microsoft Corporation. All rights reserved.
// InMemoryMessageQueue.cs

using System.Threading.Channels;
using Microsoft.AutoGen.Abstractions;
namespace Microsoft.AutoGen.Agents;
public sealed class InMemoryQueue<T> : IConnection
{
    public Task<bool> Completion { get; } = Task.FromResult(true);
    private readonly Channel<T> _channel =
        Channel.CreateUnbounded<T>();

    public ChannelReader<T> Reader => _channel.Reader;

    public ChannelWriter<T> Writer => _channel.Writer;
}
