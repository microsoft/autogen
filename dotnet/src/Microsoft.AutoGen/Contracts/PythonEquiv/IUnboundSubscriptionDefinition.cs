// Copyright (c) Microsoft Corporation. All rights reserved.
// IUnboundSubscriptionDefinition.cs

namespace Microsoft.AutoGen.Contracts.Python;

public interface IUnboundSubscriptionDefinition
{
    public ISubscriptionDefinition Bind(AgentType agentType);
}
