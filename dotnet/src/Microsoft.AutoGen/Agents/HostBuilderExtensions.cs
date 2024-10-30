using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using Google.Protobuf;
using Google.Protobuf.Reflection;
using Grpc.Core;
using Grpc.Net.Client.Configuration;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents;

public static class HostBuilderExtensions
{
    private const string _defaultAgentServiceAddress = "https://localhost:5001";
    public static AgentApplicationBuilder AddAgentWorker(this IHostApplicationBuilder builder, string agentServiceAddress = _defaultAgentServiceAddress, bool local = false)
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
        builder.Services.AddSingleton<IAgentWorkerRuntime, GrpcAgentWorkerRuntime>();
        builder.Services.AddSingleton<IHostedService>(sp => (IHostedService)sp.GetRequiredService<IAgentWorkerRuntime>());
        builder.Services.AddSingleton<AgentWorker>();
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
                                    .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(AgentBase)) && !type.IsAbstract)
                                    .Select(t => (t, t.GetInterfaces()
                                                  .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IHandle<>))
                                                  .Select(i => (GetMessageDescriptor(i.GetGenericArguments().First())?.FullName ?? "")).ToHashSet()))
                                    .ToDictionary(item => item.t, item => item.Item2);
            // if the assembly contains any interfaces of type IHandler, then add all the methods of the interface to the eventsMap
            var handlersMap = AppDomain.CurrentDomain.GetAssemblies()
                                    .SelectMany(assembly => assembly.GetTypes())
                                    .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(AgentBase)) && !type.IsAbstract)
                                    .Select(t => (t, t.GetMethods()
                                                  .Where(m => m.Name == "Handle")
                                                  .Select(m => (GetMessageDescriptor(m.GetParameters().First().ParameterType)?.FullName ?? "")).ToHashSet()))
                                    .ToDictionary(item => item.t, item => item.Item2);
            // get interfaces implemented by the agent and get the methods of the interface if they are named Handle
            var ifaceHandlersMap = AppDomain.CurrentDomain.GetAssemblies()
                                    .SelectMany(assembly => assembly.GetTypes())
                                    .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(AgentBase)) && !type.IsAbstract)
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
        return new AgentApplicationBuilder(builder);
    }

    private static MessageDescriptor? GetMessageDescriptor(Type type)
    {
        var property = type.GetProperty("Descriptor", BindingFlags.Static | BindingFlags.Public);
        return property?.GetValue(null) as MessageDescriptor;
    }
}
public sealed class ReflectionHelper
{
    public static bool IsSubclassOfGeneric(Type type, Type genericBaseType)
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
public sealed class AgentTypes(Dictionary<string, Type> types)
{
    public Dictionary<string, Type> Types { get; } = types;
    public static AgentTypes? GetAgentTypesFromAssembly()
    {
        var agents = AppDomain.CurrentDomain.GetAssemblies()
                                .SelectMany(assembly => assembly.GetTypes())
                                .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(AgentBase))
                                    && !type.IsAbstract
                                    && !type.Name.Equals("AgentWorker"))
                                .ToDictionary(type => type.Name, type => type);

        return new AgentTypes(agents);
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
    public AgentApplicationBuilder AddAgent(string typeName, Type agentType)
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, agentType));
        return this;
    }
}

