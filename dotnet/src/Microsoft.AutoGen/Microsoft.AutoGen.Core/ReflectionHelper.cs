// Copyright (c) Microsoft Corporation. All rights reserved.
// ReflectionHelper.cs

using Google.Protobuf.Reflection;
using Google.Protobuf;
using System.Reflection;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Provides helper methods for reflection operations.
/// </summary>
public static class ReflectionHelper
{
    /// <summary>
    /// Determines whether the specified type is a subclass of the specified generic base type.
    /// </summary>
    /// <param name="type">The type to check.</param>
    /// <param name="genericBaseType">The generic base type to check against.</param>
    /// <returns><c>true</c> if the specified type is a subclass of the generic base type; otherwise, <c>false</c>.</returns>
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

    /// <summary>
    /// Gets the metadata for agents from the specified assemblies.
    /// </summary>
    /// <param name="assemblies">The assemblies to scan for agent metadata.</param>
    /// <returns>An <see cref="AgentsMetadata"/> object containing the agent metadata.</returns>
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

