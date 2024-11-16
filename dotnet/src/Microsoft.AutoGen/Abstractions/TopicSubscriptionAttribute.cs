// Copyright (c) Microsoft Corporation. All rights reserved.
// TopicSubscriptionAttribute.cs

namespace Microsoft.AutoGen.Abstractions;

[AttributeUsage(AttributeTargets.All)]
public class TopicSubscriptionAttribute(string topic) : Attribute
{
    public string Topic { get; } = topic;
}
