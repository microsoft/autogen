using System.Diagnostics;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Orleans.Serialization;

namespace Microsoft.AutoGen.Runtime;

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

    public static WebApplicationBuilder AddLocalAgentService(this WebApplicationBuilder builder)
    {
        builder.WebHost.ConfigureKestrel(serverOptions =>
                        {
                            serverOptions.ListenLocalhost(5001, listenOptions =>
                            {
                                listenOptions.Protocols = HttpProtocols.Http2;
                                listenOptions.UseHttps();
                            });
                        });
        builder.AddAgentService();
        builder.UseOrleans(siloBuilder =>
        {
            siloBuilder.UseLocalhostClustering(); ;
        });
        return builder;
    }

    public static WebApplication MapAgentService(this WebApplication app)
    {
        app.MapGrpcService<WorkerGatewayService>();
        return app;
    }
}
