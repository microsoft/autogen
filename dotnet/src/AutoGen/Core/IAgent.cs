// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen;

public interface IAgent
{
    public string? Name { get; }

    public IChatLLM? ChatLLM { get; }

    /// <summary>
    /// Generate reply
    /// </summary>
    /// <param name="messages">conversation history</param>
    /// <param name="overrideOptions">completion option to override.</param>
    public Task<Message> GenerateReplyAsync(
        IEnumerable<Message> messages,
        GenerateReplyOptions? overrideOptions = null,
        CancellationToken cancellationToken = default);
}

public class GenerateReplyOptions
{
    public float? Temperature { get; set; }

    public int? MaxToken { get; set; }

    public string[]? StopSequence { get; set; }
}
