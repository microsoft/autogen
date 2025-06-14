// Copyright (c) Microsoft Corporation. All rights reserved.
// TeamState.cs

namespace Microsoft.AutoGen.AgentChat.State;

public sealed class TeamState : BaseState
{
    public required string TeamId { get; set; }
    public required SerializedState RuntimeState { get; set; }
}
