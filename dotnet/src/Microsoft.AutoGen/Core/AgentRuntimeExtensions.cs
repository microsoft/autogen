// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentRuntimeExtensions.cs

using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using System.Reflection;

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Provides extension methods for managing and registering agents within an <see cref="IAgentRuntime"/>.
/// </summary>
public static class AgentRuntimeExtensions
{
    /// <summary>
    /// Instantiates and activates an agent asynchronously using dependency injection.
    /// </summary>
    /// <param name="serviceProvider">The service provider used for dependency injection.</param>
    /// <param name="additionalArguments">Additional arguments to pass to the agent's constructor.</param>
    /// <returns>A <see cref="ValueTask{T}"/> representing the asynchronous activation of the agent.</returns>
    internal static ValueTask<IHostableAgent> ActivateAgentAsync(IServiceProvider serviceProvider, Type runtimeType, params object[] additionalArguments)
    {
        try
        {
            var agent = (IHostableAgent)ActivatorUtilities.CreateInstance(serviceProvider, runtimeType, additionalArguments);
            return ValueTask.FromResult(agent);
        }
        catch (Exception e)
        {
            return ValueTask.FromException<IHostableAgent>(e);
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
    public static ValueTask<AgentType> RegisterAgentTypeAsync<TAgent>(this IAgentRuntime runtime, AgentType type, IServiceProvider serviceProvider, params IEnumerable<object> additionalArguments) where TAgent : IHostableAgent
        => RegisterAgentTypeAsync(runtime, type, typeof(TAgent), serviceProvider, additionalArguments);

    public static ValueTask<AgentType> RegisterAgentTypeAsync(this IAgentRuntime runtime, AgentType type, Type runtimeType, IServiceProvider serviceProvider, params IEnumerable<object> additionalArguments)
    {
        Func<AgentId, IAgentRuntime, ValueTask<IHostableAgent>> factory = (id, runtime) => ActivateAgentAsync(serviceProvider, runtimeType, [id, runtime, .. additionalArguments]);
        return runtime.RegisterAgentFactoryAsync(type, factory);
    }

    private static ISubscriptionDefinition[] BindSubscriptionsForAgentType<T>(AgentType agentType, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false)
        => BindSubscriptionsForAgentType(agentType, typeof(T), skipClassSubscriptions, skipDirectMessageSubscription);

    private static ISubscriptionDefinition[] BindSubscriptionsForAgentType(AgentType agentType, Type runtimeType, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false)
    {
        // var topicAttributes = this.GetType().GetCustomAttributes<TopicSubscriptionAttribute>().Select(t => t.Topic);
        var subscriptions = new List<ISubscriptionDefinition>();

        if (!skipClassSubscriptions)
        {
            var classSubscriptions = runtimeType.GetCustomAttributes<TypeSubscriptionAttribute>().Select(t => t.Bind(agentType));
            subscriptions.AddRange(classSubscriptions);

            var prefixSubscriptions = runtimeType.GetCustomAttributes<TopicPrefixSubscriptionAttribute>().Select(t => t.Bind(agentType));
            subscriptions.AddRange(prefixSubscriptions);
        }

        if (!skipDirectMessageSubscription)
        {
            subscriptions.Add(new TypePrefixSubscription(agentType.Name + ":", agentType));
        }

        return subscriptions.ToArray();
    }

    public static async ValueTask RegisterImplicitAgentSubscriptionsAsync<TAgent>(this IAgentRuntime runtime, AgentType type, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false) where TAgent : IHostableAgent
        => await RegisterImplicitAgentSubscriptionsAsync(runtime, type, typeof(TAgent), skipClassSubscriptions, skipDirectMessageSubscription);

    public static async ValueTask RegisterImplicitAgentSubscriptionsAsync(this IAgentRuntime runtime, AgentType type, Type runtimeType, bool skipClassSubscriptions = false, bool skipDirectMessageSubscription = false)
    {
        var subscriptions = BindSubscriptionsForAgentType(type, runtimeType);
        foreach (var subscription in subscriptions)
        {
            await runtime.AddSubscriptionAsync(subscription);
        }
    }
}
