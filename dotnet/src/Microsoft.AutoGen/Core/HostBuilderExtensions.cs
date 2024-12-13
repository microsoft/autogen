// Copyright (c) Microsoft Corporation. All rights reserved.
// HostBuilderExtensions.cs

using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using Google.Protobuf;
using Google.Protobuf.Reflection;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Core;

public static class HostBuilderExtensions
{
    private const string _defaultAgentServiceAddress = "https://localhost:53071";

    public static IHostApplicationBuilder AddAgent<
        [DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)] TAgent>(this IHostApplicationBuilder builder, string typeName) where TAgent : Agent
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, typeof(TAgent)));

        return builder;
    }

    public static IHostApplicationBuilder AddAgent(this IHostApplicationBuilder builder, string typeName, Type agentType)
    {
        builder.Services.AddKeyedSingleton("AgentTypes", (sp, key) => Tuple.Create(typeName, agentType));
        return builder;
    }

    public static IHostApplicationBuilder AddAgentWorker(this IHostApplicationBuilder builder, string? agentServiceAddress = null)
    {
        agentServiceAddress ??= builder.Configuration["AGENT_HOST"] ?? _defaultAgentServiceAddress;
        builder.Services.TryAddSingleton(DistributedContextPropagator.Current);
        builder.Services.AddSingleton<IAgentWorker, AgentWorker>();
        builder.Services.AddSingleton<IHostedService>(sp => (IHostedService)sp.GetRequiredService<IAgentWorker>());
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
        builder.Services.AddSingleton<Client>();
        builder.Services.AddSingleton(new AgentApplicationBuilder(builder));

        return builder;
    }

    private static MessageDescriptor? GetMessageDescriptor(Type type)
    {
        var property = type.GetProperty("Descriptor", BindingFlags.Static | BindingFlags.Public);
        return property?.GetValue(null) as MessageDescriptor;
    }
}
public sealed class AgentApplicationBuilder(IHostApplicationBuilder builder)
{
    public AgentApplicationBuilder AddAgent<
        [DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicConstructors)] TAgent>(string typeName) where TAgent : Agent
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

