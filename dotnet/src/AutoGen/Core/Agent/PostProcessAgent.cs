// Copyright (c) Microsoft Corporation. All rights reserved.
// PostProcessAgent.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen;

public class PostProcessAgent : IAgent
{
    public PostProcessAgent(
        IAgent innerAgent,
        string name,
        Func<IEnumerable<Message>, Message, CancellationToken, Task<Message>> postprocessFunc)
    {
        InnerAgent = innerAgent;
        Name = name;
        PostprocessFunc = postprocessFunc;
    }

    public IAgent InnerAgent { get; }

    public string Name { get; }

    public Func<IEnumerable<Message>, Message, CancellationToken, Task<Message>> PostprocessFunc { get; }

    public IChatLLM? ChatLLM => InnerAgent.ChatLLM;

    public async Task<Message> GenerateReplyAsync(
        IEnumerable<Message> conversation,
        GenerateReplyOptions? options = null,
        CancellationToken ct = default)
    {
        var reply = await InnerAgent.GenerateReplyAsync(conversation, overrideOptions: options, cancellationToken: ct);
        reply.From = Name;
        return await PostprocessFunc(conversation, reply, ct);
    }
}
