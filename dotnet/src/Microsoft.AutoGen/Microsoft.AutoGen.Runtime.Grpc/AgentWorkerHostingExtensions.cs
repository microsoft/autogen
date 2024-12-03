// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorkerHostingExtensions.cs

using System.Diagnostics;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Runtime.Grpc;

public static class AgentWorkerHostingExtensions
{
    public static WebApplicationBuilder AddAgentService(this WebApplicationBuilder builder, bool inMemoryOrleans = false, bool useGrpc = true)
    {
        builder.AddOrleans(inMemoryOrleans);

        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);

        if (useGrpc)
        {
            builder.WebHost.ConfigureKestrel(serverOptions =>
            {
                // TODO: make port configurable
                serverOptions.ListenAnyIP(5001, listenOptions =>
                {
                    listenOptions.Protocols = HttpProtocols.Http2;
                    listenOptions.UseHttps();
                });
            });

            builder.Services.AddGrpc();
            builder.Services.AddSingleton<GrpcGateway>();
            builder.Services.AddSingleton(sp => (IHostedService)sp.GetRequiredService<GrpcGateway>());
        }

        return builder;
    }

    public static WebApplication MapAgentService(this WebApplication app, bool local = false, bool useGrpc = true)
    {
        if (useGrpc) { app.MapGrpcService<GrpcGatewayService>(); }
        return app;
    }
}
