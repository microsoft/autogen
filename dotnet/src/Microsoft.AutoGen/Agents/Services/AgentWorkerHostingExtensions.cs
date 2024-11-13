// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorkerHostingExtensions.cs

using System.Diagnostics;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents;

public static class AgentWorkerHostingExtensions
{
    public static WebApplicationBuilder AddAgentService(this WebApplicationBuilder builder, bool local = false, bool useGrpc = true)
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
            builder.AddOrleans(local);
        }
        else
        {
            builder.AddOrleans();
        }

        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);

        if (useGrpc)
        {
            builder.Services.AddGrpc();
            builder.Services.AddSingleton<GrpcGateway>();
            builder.Services.AddSingleton<IHostedService>(sp => (IHostedService)sp.GetRequiredService<GrpcGateway>());
        }

        return builder;
    }

    public static WebApplicationBuilder AddLocalAgentService(this WebApplicationBuilder builder, bool useGrpc = true)
    {
        return builder.AddAgentService(local: true, useGrpc);
    }
    public static WebApplication MapAgentService(this WebApplication app, bool local = false, bool useGrpc = true)
    {
        if (useGrpc) { app.MapGrpcService<GrpcGatewayService>(); }
        return app;
    }
}
