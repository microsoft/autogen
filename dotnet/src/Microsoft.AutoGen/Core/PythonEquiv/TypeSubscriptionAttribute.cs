// Copyright (c) Microsoft Corporation. All rights reserved.
// TypeSubscriptionAttribute.cs

using Microsoft.AutoGen.Contracts.Python;

namespace Microsoft.AutoGen.Core.Python;

[AttributeUsage(AttributeTargets.All)]
public class TypeSubscriptionAttribute(string topic) : Attribute, IUnboundSubscriptionDefinition
{
    public string Topic { get; } = topic;

    public ISubscriptionDefinition Bind(AgentType agentType)
    {
        return new TypeSubscription(Topic, agentType);
    }
}
