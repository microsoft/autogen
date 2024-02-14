// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Azure.AI.OpenAI;

namespace AutoGen;

public interface IAgent
{
    public string Name { get; }

    /// <summary>
    /// Generate reply
    /// </summary>
    /// <param name="messages">conversation history</param>
    /// <param name="options">completion option. If provided, it should override existing option if there's any</param>
    public Task<Message> GenerateReplyAsync(
        IEnumerable<Message> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default);
}

/// <summary>
/// agent that supports streaming reply
/// </summary>
public interface IStreamingReplyAgent : IAgent
{
    public Task<IAsyncEnumerable<IMessage>> GenerateReplyStreamingAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default);
}

public class GenerateReplyOptions
{
    public float? Temperature { get; set; }

    public int? MaxToken { get; set; }

    public string[]? StopSequence { get; set; }

    public FunctionDefinition[]? Functions { get; set; }
}
