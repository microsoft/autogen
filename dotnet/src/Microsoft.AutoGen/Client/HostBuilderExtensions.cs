// Copyright (c) Microsoft Corporation. All rights reserved.
// HostBuilderExtensions.cs

using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Provides extension methods for configuring agents and workers in a host application.
/// </summary>
public static class HostBuilderExtensions
{
    /// <summary>
    /// Adds an agent to the host application builder.
    /// </summary>
    /// <typeparam name="TAgent">The type of the agent to add.</typeparam>
    /// <param name="builder">The host application builder.</param>
    /// <param name="typeName">The name of the agent type.</param>
    /// <returns>The updated host application builder.</returns>
    public static IHostApplicationBuilder AddAgent<
        [DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)] TAgent>(this IHostApplicationBuilder builder, string typeName) where TAgent : AgentBase
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, typeof(TAgent)));

        return builder;
    }

    /// <summary>
    /// Adds an agent to the host application builder.
    /// </summary>
    /// <param name="builder">The host application builder.</param>
    /// <param name="typeName">The name of the agent type.</param>
    /// <param name="agentType">The type of the agent.</param>
    /// <returns>The updated host application builder.</returns>
    public static IHostApplicationBuilder AddAgent(this IHostApplicationBuilder builder, string typeName, Type agentType)
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, agentType));
        return builder;
    }

    /// <summary>
    /// Adds an in-memory worker to the host application builder.
    /// </summary>
    /// <param name="builder">The host application builder.</param>
    /// <returns>The updated host application builder.</returns>
    public static IHostApplicationBuilder AddInMemoryWorker(this IHostApplicationBuilder builder)
    {
        builder.Services.AddSingleton<IAgentWorker, AgentWorker>();
        return builder;
    }

    /// <summary>
    /// Adds an agent host to the host application builder.
    /// </summary>
    /// <param name="builder">The host application builder.</param>
    /// <returns>The updated host application builder.</returns>
    public static IHostApplicationBuilder AddAgentHost(this IHostApplicationBuilder builder)
    {
        var assemblies = AppDomain.CurrentDomain.GetAssemblies();
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton(sp => (IHostedService)sp.GetRequiredService<IAgentWorker>());
        builder.Services.AddKeyedSingleton("EventTypes", (sp, key) =>
        {
            return ReflectionHelper.GetAgentsMetadata(assemblies);
        });
        builder.Services.AddSingleton<Client>();

        return builder;
    }
}
