// Copyright (c) Microsoft Corporation. All rights reserved.
// IStreamingGroupChat.cs

using System.Collections.Generic;
using System.Threading;

namespace AutoGen.Core;

/// <summary>
/// A group chat that supports incremental replies from streaming agents.
/// </summary>
public interface IStreamingGroupChat : IGroupChat
{
    /// <summary>
    /// Run the group chat, yielding partial updates followed by a complete reply for each turn.
    /// Only complete replies are added to the conversation history.
    /// </summary>
    /// <param name="chatHistory">The conversation history, excluding introduction messages.</param>
    /// <param name="maxRound">The maximum number of agent turns.</param>
    /// <param name="ct">The cancellation token.</param>
    /// <returns>Partial updates and complete replies, excluding the initial history.</returns>
    IAsyncEnumerable<IMessage> CallStreamingAsync(
        IEnumerable<IMessage>? chatHistory = null,
        int maxRound = 10,
        CancellationToken ct = default);
}
