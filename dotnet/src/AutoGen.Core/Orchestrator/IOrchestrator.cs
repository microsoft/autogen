// Copyright (c) Microsoft Corporation. All rights reserved.
// IOrchestrator.cs

using System;
using System.Collections.Generic;
using System.Threading;

namespace AutoGen.Core;

public class OrchestrationContext
{
    public IEnumerable<IAgent> Candidates { get; set; } = Array.Empty<IAgent>();

    public IEnumerable<IMessage> ChatHistory { get; set; } = Array.Empty<IMessage>();
}

public interface IOrchestrator
{
    /// <summary>
    /// Return the next agent as the next speaker. It can be a single agent (single step) or multiple agents (multi-steps).
    /// </summary>
    /// <param name="context">orchestration context, such as candidate agents and chat history.</param>
    /// <param name="cancellationToken">cancellation token</param>
    public IAsyncEnumerable<IAgent> GetNextSpeakerAsync(
        OrchestrationContext context,
        int maxRound,
        CancellationToken cancellationToken = default);
}
