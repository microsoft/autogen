// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsMetadata.cs

using System.Collections.Concurrent;
using Google.Protobuf.Reflection;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Represents a collection of event types and their associated metadata.
/// </summary>
public sealed class AgentsMetadata
{
    /// <summary>
    /// Initializes a new instance of the <see cref="AgentsMetadata"/> class.
    /// </summary>
    /// <param name="typeRegistry">The type registry containing protobuf type information.</param>
    /// <param name="types">A dictionary mapping event names to their corresponding types.</param>
    /// <param name="eventsMap">A dictionary mapping types to a set of event names associated with those types.</param>
    public AgentsMetadata(TypeRegistry typeRegistry, Dictionary<string, Type> types, Dictionary<Type, HashSet<string>> eventsMap, Dictionary<Type, HashSet<string>> topicsMap)
    {
        TypeRegistry = typeRegistry;
        _types = new(types);
        _eventsMap = new(eventsMap);
        _topicsMap = new(topicsMap);
    }

    /// <summary>
    /// Gets the type registry containing protobuf type information.
    /// </summary>
    public TypeRegistry TypeRegistry { get; }

    private ConcurrentDictionary<string, Type> _types;

    private ConcurrentDictionary<Type, HashSet<string>> _eventsMap;
    private ConcurrentDictionary<Type, HashSet<string>> _topicsMap;

    /// <summary>
    /// Checks if a given type handles a specific event name.
    /// </summary>
    /// <param name="type">The type to check.</param>
    /// <param name="eventName">The event name to check.</param>
    /// <returns><c>true</c> if the type handles the event name; otherwise, <c>false</c>.</returns>
    public bool CheckIfTypeHandles(Type type, string eventName)
    {
        if (_eventsMap.TryGetValue(type, out var events))
        {
            return events.Contains(eventName);
        }
        return false;
    }

    /// <summary>
    /// Gets the event type by its name.
    /// </summary>
    /// <param name="type">The name of the event type.</param>
    /// <returns>The event type if found; otherwise, <c>null</c>.</returns>
    public Type? GetEventTypeByName(string type)
    {
        if (_types.TryGetValue(type, out var eventType))
        {
            return eventType;
        }
        return null;
    }

    public HashSet<string>? GetEventsForAgent(Type agent)
    {
        if (_eventsMap.TryGetValue(agent, out var events))
        {
            return events;
        }
        return null;
    }

    public HashSet<string>? GetTopicsForAgent(Type agent)
    {
        if (_topicsMap.TryGetValue(agent, out var topics))
        {
            return topics;
        }
        return null;
    }
}

