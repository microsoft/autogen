// Copyright (c) Microsoft Corporation. All rights reserved.
// DefaultReplyAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

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

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> _,
        GenerateReplyOptions? __ = null,
        CancellationToken ___ = default)
    {
        return new TextMessage(Role.Assistant, DefaultReply, from: this.Name);
    }
}
