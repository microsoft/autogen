// Copyright (c) Microsoft Corporation. All rights reserved.
// TopicSubscriptionAttribute.cs

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Specifies that a class or method is subscribed to a particular topic.
/// </summary>
[AttributeUsage(AttributeTargets.All)]
public class TopicSubscriptionAttribute(string topic) : Attribute
{
    /// <summary>
    /// Gets the topic to which the class or method is subscribed.
    /// </summary>
    public string Topic { get; } = topic;
}
