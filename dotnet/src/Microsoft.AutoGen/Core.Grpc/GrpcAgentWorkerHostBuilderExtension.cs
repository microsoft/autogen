// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcAgentWorkerHostBuilderExtension.cs
using System.Reflection;
using Google.Protobuf;
using Google.Protobuf.Reflection;
using Grpc.Core;
using Grpc.Net.Client.Configuration;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
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
        builder.Services.AddKeyedSingleton("EventTypes", (sp, key) =>
        {
            var interfaceType = typeof(IMessage);
            var pairs = AppDomain.CurrentDomain.GetAssemblies()
                                    .SelectMany(assembly => assembly.GetTypes())
                                    .Where(type => interfaceType.IsAssignableFrom(type) && type.IsClass && !type.IsAbstract)
                                    .Select(t => (t, GetMessageDescriptor(t)));

            var descriptors = pairs.Select(t => t.Item2);
            var typeRegistry = TypeRegistry.FromMessages(descriptors);
            var types = pairs.ToDictionary(item => item.Item2?.FullName ?? "", item => item.t);

            var eventsMap = AppDomain.CurrentDomain.GetAssemblies()
                                    .SelectMany(assembly => assembly.GetTypes())
                                    .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(Agent)) && !type.IsAbstract)
                                    .Select(t => (t, t.GetInterfaces()
                                                  .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IHandle<>))
                                                  .Select(i => (GetMessageDescriptor(i.GetGenericArguments().First())?.FullName ?? "")).ToHashSet()))
                                    .ToDictionary(item => item.t, item => item.Item2);
            // if the assembly contains any interfaces of type IHandler, then add all the methods of the interface to the eventsMap
            var handlersMap = AppDomain.CurrentDomain.GetAssemblies()
                                    .SelectMany(assembly => assembly.GetTypes())
                                    .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(Agent)) && !type.IsAbstract)
                                    .Select(t => (t, t.GetMethods()
                                                  .Where(m => m.Name == "Handle")
                                                  .Select(m => (GetMessageDescriptor(m.GetParameters().First().ParameterType)?.FullName ?? "")).ToHashSet()))
                                    .ToDictionary(item => item.t, item => item.Item2);
            // get interfaces implemented by the agent and get the methods of the interface if they are named Handle
            var ifaceHandlersMap = AppDomain.CurrentDomain.GetAssemblies()
                                    .SelectMany(assembly => assembly.GetTypes())
                                    .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(Agent)) && !type.IsAbstract)
                                    .Select(t => t.GetInterfaces()
                                                  .Select(i => (t, i, i.GetMethods()
                                                  .Where(m => m.Name == "Handle")
                                                    .Select(m => (GetMessageDescriptor(m.GetParameters().First().ParameterType)?.FullName ?? ""))
                                                    //to dictionary of type t and paramter type of the method
                                                    .ToDictionary(m => m, m => m).Keys.ToHashSet())).ToList());
            // for each item in ifaceHandlersMap, add the handlers to eventsMap with item as the key 
            foreach (var item in ifaceHandlersMap)
            {
                foreach (var iface in item)
                {
                    if (eventsMap.TryGetValue(iface.Item2, out var events))
                    {
                        events.UnionWith(iface.Item3);
                    }
                    else
                    {
                        eventsMap[iface.Item2] = iface.Item3;
                    }
                }
            }

            // merge the handlersMap into the eventsMap
            foreach (var item in handlersMap)
            {
                if (eventsMap.TryGetValue(item.Key, out var events))
                {
                    events.UnionWith(item.Value);
                }
                else
                {
                    eventsMap[item.Key] = item.Value;
                }
            }
            return new EventTypes(typeRegistry, types, eventsMap);
        });
        builder.Services.AddSingleton<IHostedService>(sp => (IHostedService)sp.GetRequiredService<IAgentWorker>());
        builder.Services.AddSingleton((s) =>
        {
            var worker = s.GetRequiredService<IAgentWorker>();
            var client = ActivatorUtilities.CreateInstance<Client>(s);
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
