// Copyright (c) Microsoft. All rights reserved.

namespace Microsoft.AutoGen.Abstractions;

[AttributeUsage(AttributeTargets.All)]
public class TopicSubscriptionAttribute(string topic) : Attribute
{
    public string Topic { get; } = topic;
}
