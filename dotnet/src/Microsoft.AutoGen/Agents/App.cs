using Google.Protobuf;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents;

public static class App
{
    // need a variable to store the runtime instance
    public static WebApplication? RuntimeApp { get; set; }
    public static WebApplication? ClientApp { get; set; }
    public static async ValueTask<WebApplication> StartAsync(AgentTypes? agentTypes = null, bool local = false)
    {
        // start the server runtime
        RuntimeApp ??= await Runtime.Host.StartAsync(local);
        var clientBuilder = WebApplication.CreateBuilder();
        clientBuilder.AddServiceDefaults();
        var appBuilder = clientBuilder.AddAgentWorker();
        agentTypes ??= AgentTypes.GetAgentTypesFromAssembly()
                   ?? throw new InvalidOperationException("No agent types found in the assembly");
        foreach (var type in agentTypes.Types)
        {
            appBuilder.AddAgent(type.Key, type.Value);
        }
        ClientApp = clientBuilder.Build();
        await ClientApp.StartAsync().ConfigureAwait(false);
        return ClientApp;
    }

    public static async ValueTask<WebApplication> PublishMessageAsync(
        string topic,
        IMessage message,
        AgentTypes? agentTypes = null,
        bool local = false)
    {
        if (ClientApp == null)
        {
            ClientApp = await App.StartAsync(agentTypes, local);
        }
        var client = ClientApp.Services.GetRequiredService<AgentClient>() ?? throw new InvalidOperationException("Client not started");
        await client.PublishEventAsync(topic, message).ConfigureAwait(false);
        return ClientApp;
    }

    public static async ValueTask ShutdownAsync()
    {
        if (ClientApp == null)
        {
            throw new InvalidOperationException("Client not started");
        }
        await ClientApp.StopAsync();
        await RuntimeApp!.StopAsync();
    }
}
