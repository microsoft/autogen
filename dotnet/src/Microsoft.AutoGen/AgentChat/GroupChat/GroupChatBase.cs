// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatBase.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public abstract class GroupChatBase<TManager> : ITeam where TManager : GroupChatManagerBase
{
    public GroupChatBase(List<IChatAgent> participants, ITerminationCondition? terminationCondition = null, int? maxTurns = null)
    {
        this.TeamId = Guid.NewGuid();
    }

    /// <summary>
    /// Gets the team id.
    /// </summary>
    public Guid TeamId
    {
        get;
        private set;
    }

    /// <inheritdoc cref="ITeam.ResetAsync(CancellationToken)"/>/>/>
    public ValueTask ResetAsync(CancellationToken cancel)
    {
        throw new NotImplementedException();
    }

    /// <inheritdoc cref="ITaskRunner.StreamAsync(ChatMessage?, CancellationToken)"/>/>/>
    public IAsyncEnumerable<TaskFrame> StreamAsync(ChatMessage? task, CancellationToken cancellationToken = default)
    {
        task = task ?? throw new ArgumentNullException(nameof(task));

        return this.StreamAsync(task, cancellationToken);
    }
}
