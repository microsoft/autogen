// Copyright (c) Microsoft Corporation. All rights reserved.
// EchoAgent.cs

using System.Runtime.CompilerServices;
using AutoGen.Core;

namespace AutoGen.WebAPI.Tests;

public class EchoAgent : IStreamingAgent
{
    public EchoAgent(string name)
    {
        Name = name;
    }
    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return messages.Last();
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var lastMessage = messages.LastOrDefault();
        if (lastMessage == null)
        {
            yield break;
        }

        // return each character of the last message as a separate message
        if (lastMessage.GetContent() is string content)
        {
            foreach (var c in content)
            {
                yield return new TextMessageUpdate(Role.Assistant, c.ToString(), this.Name);
            }
        }
    }
}
