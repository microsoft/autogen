// Copyright (c) Microsoft. All rights reserved.

using System.Collections.Generic;
using System.Threading;

namespace AutoGen.Core;

/// <summary>
/// agent that supports streaming reply
/// </summary>
public interface IStreamingAgent : IAgent
{
    public IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default);
}
