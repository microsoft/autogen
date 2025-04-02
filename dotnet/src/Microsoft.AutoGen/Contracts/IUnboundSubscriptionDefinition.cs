// Copyright (c) Microsoft Corporation. All rights reserved.
// IUnboundSubscriptionDefinition.cs

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Defines a subscription that is not yet bound to a specific agent type.
/// This interface allows the creation of dynamic subscriptions that can later be associated with an agent.
/// </summary>
public interface IUnboundSubscriptionDefinition
{
    /// <summary>
    /// Binds the subscription to a specific agent type, creating a concrete <see cref="ISubscriptionDefinition"/>.
    /// </summary>
    /// <param name="agentType">The agent type to associate with the subscription.</param>
    /// <returns>A new <see cref="ISubscriptionDefinition"/> bound to the specified agent type.</returns>
    public ISubscriptionDefinition Bind(AgentType agentType);
}
