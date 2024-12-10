// Copyright (c) Microsoft Corporation. All rights reserved.
// ITeam.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public interface ITeam : ITaskRunner
{
    ValueTask ResetAsync(CancellationToken cancellationToken = default);
}
