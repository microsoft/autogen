using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.DependencyInjection;
using Orleans.Serialization;
using Microsoft.Extensions.DependencyInjection.Extensions;
using System.Diagnostics;

namespace Microsoft.AutoGen.Agents.Runtime;

public static class AgentWorkerHostingExtensions
{
    public static IHostApplicationBuilder AddAgentService(this IHostApplicationBuilder builder)
    {
        builder.Services.AddGrpc();
        builder.Services.AddSerializer(serializer => serializer.AddProtobufSerializer());

        // Ensure Orleans is added before the hosted service to guarantee that it starts first.
        builder.UseOrleans();
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton<WorkerGateway>();
        builder.Services.AddSingleton<IHostedService>(sp => sp.GetRequiredService<WorkerGateway>());

        return builder;
    }

    public static WebApplication MapAgentService(this WebApplication app)
    {
        app.MapGrpcService<WorkerGatewayService>();
        return app;
    }
}
