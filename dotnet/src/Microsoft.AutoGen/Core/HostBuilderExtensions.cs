// Copyright (c) Microsoft Corporation. All rights reserved.
// HostBuilderExtensions.cs

using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core;

public static class HostBuilderExtensions
{
    public static IHostApplicationBuilder AddAgent<
        [DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)] TAgent>(this IHostApplicationBuilder builder, string typeName) where TAgent : Agent
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, typeof(TAgent)));

        return builder;
    }

    public static IHostApplicationBuilder AddAgent(this IHostApplicationBuilder builder, string typeName, Type agentType)
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, agentType));
        return builder;
    }

    public static IHostApplicationBuilder AddAgentWorker(this IHostApplicationBuilder builder)
    {
        var assemblies = AppDomain.CurrentDomain.GetAssemblies();
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton<IRegistryStorage, RegistryStorage>();
        builder.Services.AddSingleton<IRegistry, Registry>();
        builder.Services.AddSingleton<IAgentRuntime, AgentRuntime>();
        builder.Services.AddSingleton<IHostedService>(sp => (IHostedService)sp.GetRequiredService<IAgentRuntime>());
        builder.Services.AddKeyedSingleton("AgentsMetadata", (sp, key) =>
        {
            return ReflectionHelper.GetAgentsMetadata(assemblies);
        });
        builder.Services.AddSingleton((s) =>
        {
            var worker = s.GetRequiredService<IAgentRuntime>();
            var client = ActivatorUtilities.CreateInstance<Client>(s);
            Agent.Initialize(worker, client);
            return client;
        });
        builder.Services.AddSingleton(new AgentApplicationBuilder(builder));

        return builder;
    }
}
public sealed class AgentApplicationBuilder(IHostApplicationBuilder builder)
{
    public AgentApplicationBuilder AddAgent<
        [DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)] TAgent>(string typeName) where TAgent : Agent
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, typeof(TAgent)));
        return this;
    }
    public AgentApplicationBuilder AddAgent(string typeName, Type agentType)
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, agentType));
        return this;
    }
}

