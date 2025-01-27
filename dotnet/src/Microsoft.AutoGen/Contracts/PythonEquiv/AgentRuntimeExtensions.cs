// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntimeExtensions.cs

using Microsoft.Extensions.DependencyInjection;

namespace Microsoft.AutoGen.Contracts.Python;

/// <summary>
/// Provides extension methods for managing and registering agents within an <see cref="IAgentRuntime"/>.
/// </summary>
public static class AgentRuntimeExtensions
{
    /// <summary>
    /// Instantiates and activates an agent asynchronously using dependency injection.
    /// </summary>
    /// <typeparam name="TAgent">The type of agent to activate. Must implement <see cref="IHostableAgent"/>.</typeparam>
    /// <param name="serviceProvider">The service provider used for dependency injection.</param>
    /// <param name="additionalArguments">Additional arguments to pass to the agent's constructor.</param>
    /// <returns>A <see cref="ValueTask{T}"/> representing the asynchronous activation of the agent.</returns>
    internal static ValueTask<TAgent> ActivateAgentAsync<TAgent>(IServiceProvider serviceProvider, params object[] additionalArguments) where TAgent : IHostableAgent
    {
        try
        {
            var agent = (TAgent)ActivatorUtilities.CreateInstance(serviceProvider, typeof(TAgent), additionalArguments);
            return ValueTask.FromResult(agent);
        }
        catch (Exception e)
        {
            return ValueTask.FromException<TAgent>(e);
        }
    }

    /// <summary>
    /// Registers an agent type with the runtime, providing a factory function to create instances of the agent.
    /// </summary>
    /// <typeparam name="TAgent">The type of agent being registered. Must implement <see cref="IHostableAgent"/>.</typeparam>
    /// <param name="runtime">The <see cref="IAgentRuntime"/> where the agent will be registered.</param>
    /// <param name="type">The <see cref="AgentType"/> representing the type of agent.</param>
    /// <param name="serviceProvider">The service provider used for dependency injection.</param>
    /// <param name="additionalArguments">Additional arguments to pass to the agent's constructor.</param>
    /// <returns>A <see cref="ValueTask{AgentType}"/> representing the asynchronous operation of registering the agent.</returns>
    public static ValueTask<AgentType> RegisterAgentTypeAsync<TAgent>(this IAgentRuntime runtime, AgentType type, IServiceProvider serviceProvider, params object[] additionalArguments) where TAgent : IHostableAgent
    {
        Func<ValueTask<TAgent>> factory = () => ActivateAgentAsync<TAgent>(serviceProvider, additionalArguments);
        return runtime.RegisterAgentFactoryAsync(type, factory);
    }
}
