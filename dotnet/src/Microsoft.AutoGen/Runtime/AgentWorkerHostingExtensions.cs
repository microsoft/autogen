using System.Diagnostics;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Runtime;

public static class AgentWorkerHostingExtensions
{
    public static WebApplicationBuilder AddAgentService(this WebApplicationBuilder builder, bool local = false)
    {
        if (local)
        {
            //TODO: make configuration more flexible
            builder.WebHost.ConfigureKestrel(serverOptions =>
                        {
                            serverOptions.ListenLocalhost(5001, listenOptions =>
                            {
                                listenOptions.Protocols = HttpProtocols.Http2;
                                listenOptions.UseHttps();
                            });
                        });
        }
        builder.Services.AddGrpc();
        builder.AddOrleans(local);
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton<WorkerGateway>();
        builder.Services.AddSingleton<IHostedService>(sp => sp.GetRequiredService<WorkerGateway>());

        return builder;
    }

    public static WebApplicationBuilder AddLocalAgentService(this WebApplicationBuilder builder)
    {
        builder.AddAgentService(local: true);
        return builder;
    }
    public static WebApplication MapAgentService(this WebApplication app)
    {
        app.MapGrpcService<WorkerGatewayService>();
        return app;
    }
}
