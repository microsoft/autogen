// Copyright (c) Microsoft Corporation. All rights reserved.
// TypePrefixSubscriptionAttribute.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core;

[AttributeUsage(AttributeTargets.All)]
public class TopicPrefixSubscriptionAttribute(string topic) : Attribute, IUnboundSubscriptionDefinition
{
    public string Topic { get; } = topic;

    public ISubscriptionDefinition Bind(AgentType agentType)
    {
        return new TypePrefixSubscription(Topic, agentType);
    }
}
