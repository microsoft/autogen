using Microsoft.AspNetCore.Builder;

namespace Microsoft.AutoGen.Agents.Client;

public static class App
{
    public static async Task<WebApplication> StartAsync<T>(string name) where T : AgentBase
    {
        var clientBuilder = WebApplication.CreateBuilder();
        clientBuilder.AddLocalAgentWorker().AddAgent<T>(name);
        var clientApp = clientBuilder.Build();
        await clientApp.StartAsync().ConfigureAwait(false);
        return clientApp;
    }
}