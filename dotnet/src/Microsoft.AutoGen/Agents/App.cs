// Copyright (c) Microsoft Corporation. All rights reserved.
// App.cs
using System.Diagnostics.CodeAnalysis;
using Google.Protobuf;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents;

public static class AgentsApp
{
    // need a variable to store the runtime instance
    public static WebApplication? Host { get; private set; }

    [MemberNotNull(nameof(Host))]
    public static async ValueTask<WebApplication> StartAsync(WebApplicationBuilder? builder = null, AgentTypes? agentTypes = null, bool local = false)
    {
        builder ??= WebApplication.CreateBuilder();
        if (local)
        {
            // start the server runtime
            builder.AddLocalAgentService(useGrpc: false);
        }
        builder.AddAgentWorker(local: local)
            .AddAgents(agentTypes);
        builder.AddServiceDefaults();
        var app = builder.Build();
        if (local)
        {
            app.MapAgentService(local: true, useGrpc: false);
        }
        app.MapDefaultEndpoints();
        Host = app;
        await app.StartAsync().ConfigureAwait(false);
        return Host;
    }
    public static async ValueTask<WebApplication> PublishMessageAsync(
        string topic,
        IMessage message,
        WebApplicationBuilder? builder = null,
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
