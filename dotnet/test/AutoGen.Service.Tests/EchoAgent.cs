// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionMiddlewareTests.cs

using AutoGen.Core;

namespace AutoGen.Service.Tests;

public class EchoAgent : IAgent
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
}
