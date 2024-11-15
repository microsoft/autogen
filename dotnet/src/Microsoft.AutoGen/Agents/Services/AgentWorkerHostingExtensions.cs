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
            builder.WebHost.ConfigureKestrel(serverOptions =>
                        {
                            serverOptions.ListenAnyIP(5001, listenOptions =>
                            {
                                listenOptions.Protocols = HttpProtocols.Http2;
                                listenOptions.UseHttps();
                            });
                        });
            builder.AddOrleans(local);

        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);

        if (useGrpc)
        {
            builder.Services.AddGrpc();
            builder.Services.AddSingleton<GrpcGateway>();
            builder.Services.AddSingleton<IHostedService>(sp => sp.GetRequiredService<GrpcGateway>());
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
