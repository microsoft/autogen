// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsApp.cs

using Google.Protobuf;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using System.Diagnostics.CodeAnalysis;

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
            builder.AddInMemoryWorker();
            builder.AddAgentHost();
            builder.AddAgents(agentTypes);
        }
       
        //builder.AddServiceDefaults();
        var app = builder.Build();
        if (local)
        {
           // app.MapAgentService(local: true, useGrpc: false);
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
        await client.PublishEventAsync(message, topic, new CancellationToken()).ConfigureAwait(true);
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
public sealed class AgentTypes(Dictionary<string, Type> types)
{
    public Dictionary<string, Type> Types { get; } = types;
    public static AgentTypes? GetAgentTypesFromAssembly()
    {
        var agents = AppDomain.CurrentDomain.GetAssemblies()
                                .SelectMany(assembly => assembly.GetTypes())
                                .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(Agent))
                                    && !type.IsAbstract
                                    && !type.Name.Equals(nameof(Client)))
                                .ToDictionary(type => type.Name, type => type);

        return new AgentTypes(agents);
    }
}
