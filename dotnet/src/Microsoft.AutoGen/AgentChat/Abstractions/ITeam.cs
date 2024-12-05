// Copyright (c) Microsoft Corporation. All rights reserved.
// ITeam.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

internal interface ITeam : ITaskRunner
{
    ValueTask ResetAsync(CancellationToken cancellationToken = default);
}
