using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using Google.Protobuf;
using Google.Protobuf.Reflection;
using Grpc.Core;
using Grpc.Net.Client.Configuration;
using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents.Client;

public static class HostBuilderExtensions
{
    public static AgentApplicationBuilder AddAgentWorker(this IHostApplicationBuilder builder, string agentServiceAddress)
    {
        builder.Services.AddGrpcClient<AgentRpc.AgentRpcClient>(options =>
        {
            options.Address = new Uri(agentServiceAddress);
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
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton<AgentWorkerRuntime>();
        builder.Services.AddSingleton<IHostedService>(sp => sp.GetRequiredService<AgentWorkerRuntime>());
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
                                    .Where(type => IsSubclassOfGeneric(type, typeof(AiAgent<>)) && !type.IsAbstract)
                                    .Select(t => (t, t.GetInterfaces()
                                                  .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IHandle<>))
                                                  .Select(i => (GetMessageDescriptor(i.GetGenericArguments().First())?.FullName ?? "")).ToHashSet()))
                                    .ToDictionary(item => item.t, item => item.Item2);

            return new EventTypes(typeRegistry, types, eventsMap);
        });
        return new AgentApplicationBuilder(builder);
    }

    private static MessageDescriptor? GetMessageDescriptor(Type type)
    {
        var property = type.GetProperty("Descriptor", BindingFlags.Static | BindingFlags.Public);
        return property?.GetValue(null) as MessageDescriptor;
    }

    private static bool IsSubclassOfGeneric(Type type, Type genericBaseType)
    {
        while (type != null && type != typeof(object))
        {
            if (genericBaseType == (type.IsGenericType ? type.GetGenericTypeDefinition() : type))
            {
                return true;
            }
            if (type.BaseType == null)
            {
                return false;
            }
            type = type.BaseType;
        }
        return false;
    }
}

public sealed class EventTypes(TypeRegistry typeRegistry, Dictionary<string, Type> types, Dictionary<Type, HashSet<string>> eventsMap)
{
    public TypeRegistry TypeRegistry { get; } = typeRegistry;
    public Dictionary<string, Type> Types { get; } = types;
    public Dictionary<Type, HashSet<string>> EventsMap { get; } = eventsMap;
}

public sealed class AgentApplicationBuilder(IHostApplicationBuilder builder)
{
    public AgentApplicationBuilder AddAgent<
        [DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)] TAgent>(string typeName) where TAgent : AgentBase
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, typeof(TAgent)));
        return this;
    }
}

