// Copyright (c) Microsoft Corporation. All rights reserved.
// ISubscriptionDefinition.cs

using System.Diagnostics.CodeAnalysis;

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Defines a subscription that matches topics and maps them to agents.
/// </summary>
public interface ISubscriptionDefinition
{
    /// <summary>
    /// Gets the unique identifier of the subscription.
    /// </summary>
    public string Id { get; }

    /// <summary>
    /// Determines whether the specified object is equal to the current subscription.
    /// </summary>
    /// <param name="obj">The object to compare with the current instance.</param>
    /// <returns><c>true</c> if the specified object is equal to this instance; otherwise, <c>false</c>.</returns>
    public bool Equals([NotNullWhen(true)] object? obj) => obj is ISubscriptionDefinition other && Equals(other);

    /// <summary>
    /// Determines whether the specified subscription is equal to the current subscription.
    /// </summary>
    /// <param name="other">The subscription to compare.</param>
    /// <returns><c>true</c> if the subscriptions are equal; otherwise, <c>false</c>.</returns>
    public bool Equals(ISubscriptionDefinition? other) => Id == other?.Id;

    /// <summary>
    /// Returns a hash code for this subscription.
    /// </summary>
    /// <returns>A hash code for the subscription.</returns>
    public int GetHashCode() => Id.GetHashCode();

    /// <summary>
    /// Checks if a given <see cref="TopicId"/> matches the subscription.
    /// </summary>
    /// <param name="topic">The topic to check.</param>
    /// <returns><c>true</c> if the topic matches the subscription; otherwise, <c>false</c>.</returns>
    public bool Matches(TopicId topic);

    /// <summary>
    /// Maps a <see cref="TopicId"/> to an <see cref="AgentId"/>.
    /// Should only be called if <see cref="Matches"/> returns <c>true</c>.
    /// </summary>
    /// <param name="topic">The topic to map.</param>
    /// <returns>The <see cref="AgentId"/> that should handle the topic.</returns>
    public AgentId MapToAgent(TopicId topic);
}

