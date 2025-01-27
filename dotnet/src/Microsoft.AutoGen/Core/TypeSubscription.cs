// Copyright (c) Microsoft Corporation. All rights reserved.
// TypeSubscription.cs

using System.Diagnostics.CodeAnalysis;

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// This subscription matches on topics based on the exact type and maps to agents using the source of the topic as the agent key.
/// This subscription causes each source to have its own agent instance.
/// </summary>
/// <remarks>
/// Example:
/// <code>
/// var subscription = new TypeSubscription("t1", "a1");
/// </code>
/// In this case:
/// - A <see cref="TopicId"/> with type `"t1"` and source `"s1"` will be handled by an agent of type `"a1"` with key `"s1"`.
/// - A <see cref="TopicId"/> with type `"t1"` and source `"s2"` will be handled by an agent of type `"a1"` with key `"s2"`.
/// </remarks>
public class TypeSubscription : ISubscriptionDefinition
{
    private readonly string _topicType;
    private readonly AgentType _agentType;
    private readonly string _id;

    /// <summary>
    /// Initializes a new instance of the <see cref="TypeSubscription"/> class.
    /// </summary>
    /// <param name="topicType">The exact topic type to match against.</param>
    /// <param name="agentType">Agent type to handle this subscription.</param>
    /// <param name="id">Unique identifier for the subscription. If not provided, a new UUID will be generated.</param>
    public TypeSubscription(string topicType, AgentType agentType, string? id = null)
    {
        _topicType = topicType;
        _agentType = agentType;
        _id = id ?? Guid.NewGuid().ToString();
    }

    /// <summary>
    /// Gets the unique identifier of the subscription.
    /// </summary>
    public string Id => _id;

    /// <summary>
    /// Gets the exact topic type used for matching.
    /// </summary>
    public string TopicType => _topicType;

    /// <summary>
    /// Gets the agent type that handles this subscription.
    /// </summary>
    public AgentType AgentType => _agentType;

    /// <summary>
    /// Checks if a given <see cref="TopicId"/> matches the subscription based on an exact type match.
    /// </summary>
    /// <param name="topic">The topic to check.</param>
    /// <returns><c>true</c> if the topic's type matches exactly, <c>false</c> otherwise.</returns>
    public bool Matches(TopicId topic)
    {
        return topic.Type == _topicType;
    }

    /// <summary>
    /// Maps a <see cref="TopicId"/> to an <see cref="AgentId"/>. Should only be called if <see cref="Matches"/> returns true.
    /// </summary>
    /// <param name="topic">The topic to map.</param>
    /// <returns>An <see cref="AgentId"/> representing the agent that should handle the topic.</returns>
    /// <exception cref="InvalidOperationException">Thrown if the topic does not match the subscription.</exception>
    public AgentId MapToAgent(TopicId topic)
    {
        if (!Matches(topic))
        {
            throw new InvalidOperationException("TopicId does not match the subscription.");
        }

        return new AgentId(_agentType, topic.Source);
    }

    /// <summary>
    /// Determines whether the specified object is equal to the current subscription.
    /// </summary>
    /// <param name="obj">The object to compare with the current instance.</param>
    /// <returns><c>true</c> if the specified object is equal to this instance; otherwise, <c>false</c>.</returns>
    public override bool Equals([NotNullWhen(true)] object? obj)
    {
        return obj is TypeSubscription other &&
               (Id == other.Id ||
               (AgentType == other.AgentType && TopicType == other.TopicType));
    }

    /// <summary>
    /// Returns a hash code for this instance.
    /// </summary>
    /// <returns>A hash code for this instance, suitable for use in hashing algorithms and data structures.</returns>
    public override int GetHashCode()
    {
        return HashCode.Combine(Id, AgentType, TopicType);
    }
}
