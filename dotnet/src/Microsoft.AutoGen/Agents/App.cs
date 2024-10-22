using System.Diagnostics.CodeAnalysis;
using Google.Protobuf;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Runtime;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents;

public static class AgentsApp
{
    // need a variable to store the runtime instance
    public static WebApplication? Host { get; private set; }
    public static WebApplicationBuilder ClientBuilder { get; } = WebApplication.CreateBuilder();
    public static WebApplicationBuilder CreateBuilder(AgentTypes? agentTypes = null, bool local = false)
    {
        ClientBuilder.AddServiceDefaults();
        ClientBuilder.AddAgentWorker().AddAgents(agentTypes);
        return ClientBuilder;
    }
    [MemberNotNull(nameof(Host))]
    public static async ValueTask<WebApplication> StartAsync(WebApplicationBuilder? builder = null, AgentTypes? agentTypes = null, bool local = false)
    {
        // start the server runtime
        if (builder == null)
        {
            builder = WebApplication.CreateBuilder();
        }
        if (local)
        {
            builder.AddLocalAgentService();
        }
        else
        {
            builder.AddAgentService();
        }
        builder.AddAgentWorker()
            .AddAgents(agentTypes);
        var app = builder.Build();
        app.MapAgentService();
        Host = app;
        await app.StartAsync().ConfigureAwait(false);
        return Host;
    }
    public static async ValueTask<WebApplication> PublishMessageAsync(
        string topic,
        IMessage message,
        WebApplicationBuilder? builder = null,
        AgentTypes? agentTypes = null,
        bool local = false)
    {
        if (Host == null)
        {
            await StartAsync(builder, agentTypes, local);
        }
        var client = Host.Services.GetRequiredService<AgentClient>() ?? throw new InvalidOperationException("Host not started");
        await client.PublishEventAsync(topic, message).ConfigureAwait(false);
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

    private static AgentApplicationBuilder AddAgents(this AgentApplicationBuilder builder, AgentTypes? agentTypes)
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
