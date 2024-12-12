// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorkerHostingExtensions.cs

using System.Diagnostics;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Runtime.Grpc;

public static class AgentWorkerHostingExtensions
{
    public static WebApplicationBuilder AddAgentService(this WebApplicationBuilder builder, bool local = false, bool useGrpc = true)
    {
        builder.AddOrleans(local);

        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);

        if (useGrpc)
        {
            builder.Services.AddGrpc();
            builder.Services.AddSingleton<GrpcGateway>();
            builder.Services.AddSingleton<IHostedService>(sp => (IHostedService)sp.GetRequiredService<GrpcGateway>());
        }

        return builder;
    }

    public static WebApplication MapAgentService(this WebApplication app, bool local = false, bool useGrpc = true)
    {
        if (useGrpc) { app.MapGrpcService<GrpcGatewayService>(); }
        return app;
    }
}
