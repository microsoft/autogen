// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsAppBuilderExtensions.cs

using System.Diagnostics;
using Grpc.Core;
using Grpc.Net.Client.Configuration;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
namespace Microsoft.AutoGen.Core.Grpc;

public static class AgentsAppBuilderExtensions
{
    private const string _defaultAgentServiceAddress = "http://localhost:53071";

    // TODO: How do we ensure AddGrpcAgentWorker and UseInProcessRuntime are mutually exclusive?
    public static AgentsAppBuilder AddGrpcAgentWorker(this AgentsAppBuilder builder, string? agentServiceAddress = null)
    {
        builder.Services.AddGrpcClient<AgentRpc.AgentRpcClient>(options =>
        {
            options.Address = new Uri(agentServiceAddress ?? builder.Configuration.GetValue("AGENT_HOST", _defaultAgentServiceAddress));
            options.ChannelOptionsActions.Add(channelOptions =>
            {
                var loggerFactory = new LoggerFactory();
                if (Debugger.IsAttached)
                {
                    channelOptions.HttpHandler = new SocketsHttpHandler
                    {
                        EnableMultipleHttp2Connections = false,
                        KeepAlivePingDelay = TimeSpan.FromSeconds(200),
                        KeepAlivePingTimeout = TimeSpan.FromSeconds(100),
                        KeepAlivePingPolicy = HttpKeepAlivePingPolicy.Always
                    };
                }
                else
                {
                    channelOptions.HttpHandler = new SocketsHttpHandler
                    {
                        EnableMultipleHttp2Connections = true,
                        KeepAlivePingDelay = TimeSpan.FromSeconds(20),
                        KeepAlivePingTimeout = TimeSpan.FromSeconds(10),
                        KeepAlivePingPolicy = HttpKeepAlivePingPolicy.WithActiveRequests
                    };
                }

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

        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton<IAgentRuntime, GrpcAgentRuntime>();
        builder.Services.AddHostedService<GrpcAgentRuntime>(services =>
        {
            return (services.GetRequiredService<IAgentRuntime>() as GrpcAgentRuntime)!;
        });

        return builder;
    }
}
