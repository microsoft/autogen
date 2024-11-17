// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentWorkerHostBuilderExtension.cs

using Grpc.Core;
using Grpc.Net.Client.Configuration;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents;

public static class GrpcAgentWorkerHostBuilderExtensions
{
    private const string _defaultAgentServiceAddress = "https://localhost:53071";
    public static IHostApplicationBuilder AddGrpcAgentWorker(this IHostApplicationBuilder builder, string? agentServiceAddress = null)
    {
        builder.Services.AddGrpcClient<AgentRpc.AgentRpcClient>(options =>
        {
            options.Address = new Uri(agentServiceAddress ?? builder.Configuration["AGENT_HOST"] ?? _defaultAgentServiceAddress);
            options.ChannelOptionsActions.Add(channelOptions =>
            {

                channelOptions.HttpHandler = new SocketsHttpHandler
                {
                    EnableMultipleHttp2Connections = true,
                    KeepAlivePingDelay = TimeSpan.FromSeconds(20),
                    KeepAlivePingTimeout = TimeSpan.FromSeconds(10),
                    KeepAlivePingPolicy = HttpKeepAlivePingPolicy.WithActiveRequests
                };

                var methodConfig = new MethodConfig
                {
                    Names = { MethodName.Default },
                    RetryPolicy = new RetryPolicy
                    {
                        MaxAttempts = 5,
                        InitialBackoff = TimeSpan.FromSeconds(1),
                        MaxBackoff = TimeSpan.FromSeconds(5),
                        BackoffMultiplier = 1.5,
                        RetryableStatusCodes = { StatusCode.Unavailable }
                    }
                };

                channelOptions.ServiceConfig = new() { MethodConfigs = { methodConfig } };
                channelOptions.ThrowOperationCanceledOnCancellation = true;
            });
        });
        builder.Services.AddSingleton<IAgentWorker, GrpcAgentWorker>();
        return builder;
    }
}
