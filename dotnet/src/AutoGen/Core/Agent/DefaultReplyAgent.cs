// Copyright (c) Microsoft Corporation. All rights reserved.
// DefaultReplyAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen;

public class DefaultReplyAgent : IAgent
{
    public DefaultReplyAgent(
        string name,
        string? defaultReply)
    {
        Name = name;
        DefaultReply = defaultReply ?? string.Empty;
    }

    public string Name { get; }

    public string DefaultReply { get; } = string.Empty;

    public IChatLLM? ChatLLM => null;

    public async Task<Message> GenerateReplyAsync(
        IEnumerable<Message> _,
        GenerateReplyOptions? __ = null,
        CancellationToken ___ = default)
    {
        return new Message(Role.Assistant, DefaultReply, from: this.Name);
    }
}
