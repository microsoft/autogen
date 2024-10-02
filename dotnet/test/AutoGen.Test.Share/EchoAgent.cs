// Copyright (c) Microsoft Corporation. All rights reserved.
// EchoAgent.cs

using System.Runtime.CompilerServices;
using AutoGen.Core;

namespace AutoGen.Tests;

public class EchoAgent : IStreamingAgent
{
    public EchoAgent(string name)
    {
        Name = name;
    }
    public string Name { get; }

    public Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> conversation,
        GenerateReplyOptions? options = null,
        CancellationToken ct = default)
    {
        // return the most recent message
        var lastMessage = conversation.Last();
        lastMessage.From = this.Name;

        return Task.FromResult(lastMessage);
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        foreach (var message in messages)
        {
            message.From = this.Name;
            yield return message;
        }
    }
}
