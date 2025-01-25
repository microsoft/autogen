// Copyright (c) Microsoft Corporation. All rights reserved.
// ReflectionHelper.cs
using System.Reflection;
using Google.Protobuf;
using Google.Protobuf.Reflection;

namespace Microsoft.AutoGen.Core;
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
    public static AgentsMetadata GetAgentsMetadata(params Assembly[] assemblies)
    {
        var interfaceType = typeof(IMessage);
        var pairs = assemblies
                                .SelectMany(assembly => assembly.GetTypes())
                                .Where(type => interfaceType.IsAssignableFrom(type) && type.IsClass && !type.IsAbstract)
                                .Select(t => (t, GetMessageDescriptor(t)));

        var descriptors = pairs.Select(t => t.Item2);
        var typeRegistry = TypeRegistry.FromMessages(descriptors);
        var types = pairs.ToDictionary(item => item.Item2?.FullName ?? "", item => item.t);

        var eventsMap = assemblies
                                .SelectMany(assembly => assembly.GetTypes())
                                .Where(type => IsSubclassOfGeneric(type, typeof(Agent)) && !type.IsAbstract)
                                .Select(t => (t, t.GetInterfaces()
                                              .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IHandle<>))
                                              .Select(i => GetMessageDescriptor(i.GetGenericArguments().First())?.FullName ?? "").ToHashSet()))
                                .ToDictionary(item => item.t, item => item.Item2);
        var topicsMap = assemblies
                               .SelectMany(assembly => assembly.GetTypes())
                               .Where(type => IsSubclassOfGeneric(type, typeof(Agent)) && !type.IsAbstract)
                               .Select(t => (t, t.GetCustomAttributes<TopicSubscriptionAttribute>().Select(a => a.Topic).ToHashSet()))
                               .ToDictionary(item => item.t, item => item.Item2);
        return new AgentsMetadata(typeRegistry, types, eventsMap, topicsMap);
    }

    /// <summary>
    /// Gets the message descriptor for the specified type.
    /// </summary>
    /// <param name="type">The type to get the message descriptor for.</param>
    /// <returns>The message descriptor if found; otherwise, <c>null</c>.</returns>
    public static MessageDescriptor? GetMessageDescriptor(Type type)
    {
        var property = type.GetProperty("Descriptor", BindingFlags.Static | BindingFlags.Public);
        return property?.GetValue(null) as MessageDescriptor;
    }
}
