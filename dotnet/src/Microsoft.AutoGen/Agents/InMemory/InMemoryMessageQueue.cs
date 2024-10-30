// Copyright (c) Microsoft Corporation. All rights reserved.
// InMemoryMessageQueue.cs

using System.Threading.Channels;
namespace Microsoft.AutoGen.Agents;
internal sealed class InMemoryQueue<T>
{
    private readonly Channel<T> _channel =
        Channel.CreateUnbounded<T>();

    public ChannelReader<T> Reader => _channel.Reader;

    public ChannelWriter<T> Writer => _channel.Writer;
}
