// Copyright (c) Microsoft Corporation. All rights reserved.
// App.cs
using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;
using Google.Protobuf;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core.Grpc;

public static class AgentsApp
{
    // need a variable to store the runtime instance
    public static IHost? Host { get; private set; }

    [MemberNotNull(nameof(Host))]
    public static async ValueTask<IHost> StartAsync(HostApplicationBuilder? builder = null, AgentTypes? agentTypes = null, bool local = false)
    {
        builder ??= new HostApplicationBuilder();
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        if (!local)
        {
            builder.AddGrpcAgentWorker()
            .AddAgents(agentTypes);
        }
        else
        {
            builder.AddAgentWorker()
            .AddAgents(agentTypes);
        }
        var app = builder.Build();
        Host = app;
        await app.StartAsync().ConfigureAwait(false);
        return Host;
    }
    public static async ValueTask<IHost> PublishMessageAsync(
        string topic,
        IMessage message,
        HostApplicationBuilder? builder = null,
        AgentTypes? agents = null,
        bool local = false)
    {
        if (Host == null)
        {
            await StartAsync(builder, agents, local);
        }
        var client = Host.Services.GetRequiredService<Client>() ?? throw new InvalidOperationException("Host not started");
        await client.PublishEventAsync(topic, message, new CancellationToken()).ConfigureAwait(true);
        return Host;
    }
    public static async ValueTask ShutdownAsync()
    {
        if (Host == null)
        {
            throw new InvalidOperationException("Host not started");
        }
        await Host.StopAsync();
    }

    private static IHostApplicationBuilder AddAgents(this IHostApplicationBuilder builder, AgentTypes? agentTypes)
    {
        agentTypes ??= AgentTypes.GetAgentTypesFromAssembly()
                   ?? throw new InvalidOperationException("No agent types found in the assembly");
        foreach (var type in agentTypes.Types)
        {
            builder.AddAgent(type.Key, type.Value);
        }
        return builder;
    }
}
