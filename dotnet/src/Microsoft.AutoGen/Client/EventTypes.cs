// Copyright (c) Microsoft Corporation. All rights reserved.
// EventTypes.cs

using System.Collections.Concurrent;
using Google.Protobuf.Reflection;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Represents a collection of event types and their associated metadata.
/// </summary>
public sealed class EventTypes
{
    /// <summary>
    /// Initializes a new instance of the <see cref="EventTypes"/> class.
    /// </summary>
    /// <param name="typeRegistry">The type registry containing protobuf type information.</param>
    /// <param name="types">A dictionary mapping event names to their corresponding types.</param>
    /// <param name="eventsMap">A dictionary mapping types to a set of event names associated with those types.</param>
    public EventTypes(TypeRegistry typeRegistry, Dictionary<string, Type> types, Dictionary<Type, HashSet<string>> eventsMap)
    {
        TypeRegistry = typeRegistry;
        _types = new(types);
        _eventsMap = new(eventsMap);
    }

    /// <summary>
    /// Gets the type registry containing protobuf type information.
    /// </summary>
    public TypeRegistry TypeRegistry { get; }

    private ConcurrentDictionary<string, Type> _types;

    private ConcurrentDictionary<Type, HashSet<string>> _eventsMap;

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
}

