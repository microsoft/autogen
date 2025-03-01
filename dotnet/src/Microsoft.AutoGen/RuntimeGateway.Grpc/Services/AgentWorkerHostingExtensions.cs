// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentWorkerHostingExtensions.cs

using System.Diagnostics;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc;
public static class AgentWorkerHostingExtensions
{
    /// <summary>
    /// Adds the Agent Runtime Gateway Service to the web application.
    /// </summary>
    /// <param name="builder">The builder for the application.</param>
    /// <param name="supportAgentTypeMultiplexing">
    /// Whether the gateway should be configured to support multiple runtime clients registering a new agent. The behaviour
    /// defaults to <c>false</c> which is consistent with the Python Agent Runtime Gateway. This flag should be thought of
    /// as experimental and possibly obsolete capability.
    /// </param>
    /// <returns>The builder for the application</returns>
    public static WebApplicationBuilder AddAgentService(this WebApplicationBuilder builder, bool supportAgentTypeMultiplexing = false)
    {
        builder.AddOrleans();

        OptionsBuilder<GrpcGatewayOptions> optionsBuilder = builder.Services.AddOptions<GrpcGatewayOptions>();

        if (supportAgentTypeMultiplexing)
        {
            optionsBuilder.Configure(options => options.SupportAgentTypeMultiplexing = supportAgentTypeMultiplexing );
        }

        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);

        builder.Services.AddGrpc();
        builder.Services.AddSingleton<GrpcGateway>();
        builder.Services.AddSingleton<IHostedService>(sp => (IHostedService)sp.GetRequiredService<GrpcGateway>());

        return builder;
    }

    public static WebApplication MapAgentService(this WebApplication app, bool local = false, bool useGrpc = true)
    {
        if (useGrpc) { app.MapGrpcService<GrpcGatewayService>(); }
        return app;
    }
}
