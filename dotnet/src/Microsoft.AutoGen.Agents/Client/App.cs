using System.Diagnostics.CodeAnalysis;
using Google.Protobuf;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Agents.Runtime;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents.Client;

public static class App
{
    // need a variable to store the runtime instance
    public static WebApplication? Host { get; set; }

    [MemberNotNull(nameof(Host))]
    public static async ValueTask<WebApplication> StartAsync(AgentTypes? agentTypes = null, bool local = false)
    {
        // start the server runtime
        var builder = WebApplication.CreateBuilder();
        if (local)
        {
            builder.AddLocalAgentService();
        }
        else
        {
            builder.AddAgentService();
        }
        var worker = builder.AddAgentWorker();
        builder.AddServiceDefaults();
        agentTypes ??= AgentTypes.GetAgentTypesFromAssembly()
                   ?? throw new InvalidOperationException("No agent types found in the assembly");
        foreach (var type in agentTypes.Types)
        {
            worker.AddAgent(type.Key, type.Value);
        }

        var app = builder.Build();
        app.MapAgentService();
        Host = app;
        await app.StartAsync().ConfigureAwait(false);
        return Host;
    }

    public static async ValueTask<WebApplication> PublishMessageAsync(
        string topic,
        IMessage message,
        AgentTypes? agentTypes = null,
        bool local = false)
    {
        if (Host == null)
        {
            await StartAsync(agentTypes, local);
        }
        var client = Host.Services.GetRequiredService<AgentClient>() ?? throw new InvalidOperationException("Host not started.");
        await client.PublishEventAsync(topic, message).ConfigureAwait(false);
        return Host;
    }

    public static async ValueTask ShutdownAsync()
    {
        if (Host == null)
        {
            throw new InvalidOperationException("Host not started.");
        }

        await Host.StopAsync();
    }
}
