// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentWorkerHostBuilderExtension.cs
using System.Diagnostics;
using System.Reflection;
using Google.Protobuf.Reflection;
using Grpc.Core;
using Grpc.Net.Client.Configuration;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
namespace Microsoft.AutoGen.Core.Grpc;

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
        var assemblies = AppDomain.CurrentDomain.GetAssemblies();
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton<IRegistryStorage, RegistryStorage>();
        builder.Services.AddSingleton<IRegistry, Registry>();
        builder.Services.AddSingleton<IAgentRuntime, GrpcAgentRuntime>();
        builder.Services.AddSingleton<IHostedService>(sp => (IHostedService)sp.GetRequiredService<IAgentRuntime>());
        builder.Services.AddKeyedSingleton("AgentsMetadata", (sp, key) =>
        {
            return ReflectionHelper.GetAgentsMetadata(assemblies);
        });
        builder.Services.AddSingleton((s) =>
        {
            var worker = s.GetRequiredService<IAgentRuntime>();
            var client = ActivatorUtilities.CreateInstance<Client>(s);
            Agent.Initialize(worker, client);
            return client;
        });
        builder.Services.AddSingleton(new AgentApplicationBuilder(builder));
        return builder;
    }
    private static MessageDescriptor? GetMessageDescriptor(Type type)
    {
        var property = type.GetProperty("Descriptor", BindingFlags.Static | BindingFlags.Public);
        return property?.GetValue(null) as MessageDescriptor;
    }
}
