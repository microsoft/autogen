// Copyright (c) Microsoft Corporation. All rights reserved.
// ISubscriptionDefinition.cs

using System.Diagnostics.CodeAnalysis;

namespace Microsoft.AutoGen.Contracts.Python;

public interface ISubscriptionDefinition
{
    public string Id { get; }

    public bool Equals([NotNullWhen(true)] object? obj) => obj is ISubscriptionDefinition other && Equals(other);
    public bool Equals(ISubscriptionDefinition? other) => Id == other?.Id;

    public int GetHashCode() => Id.GetHashCode();

    public bool Matches(TopicId topic);
    public AgentId MapToAgent(TopicId topic);
}

