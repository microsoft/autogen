using Microsoft.AspNetCore.Builder;

namespace Microsoft.AutoGen.Agents.Client;

public static class App
{
    // need a variable to store the runtime instance
    public static WebApplication? RuntimeApp { get; set; }
    public static async Task<WebApplication> StartAsync(AgentTypes? agentTypes = null, bool local = false)
    {
        if (RuntimeApp == null)
        {
            // start the server runtime
            RuntimeApp = await Runtime.Host.StartAsync(local);
        }
        var clientBuilder = WebApplication.CreateBuilder();
        var appBuilder = clientBuilder.AddAgentWorker();
        agentTypes ??= AgentTypes.GetAgentTypesFromAssembly()
                   ?? throw new InvalidOperationException("No agent types found in the assembly");
        foreach (var type in agentTypes.Types)
        {
            appBuilder.AddAgent(type.Key, type.Value);
        }
        var clientApp = clientBuilder.Build();
        await clientApp.StartAsync().ConfigureAwait(false);
        return clientApp;
    }
}