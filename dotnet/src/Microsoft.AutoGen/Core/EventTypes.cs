// Copyright (c) Microsoft Corporation. All rights reserved.
// EventTypes.cs
using Google.Protobuf.Reflection;

namespace Microsoft.AutoGen.Core;
public sealed class EventTypes(TypeRegistry typeRegistry, Dictionary<string, Type> types, Dictionary<Type, HashSet<string>> eventsMap)
{
    public TypeRegistry TypeRegistry { get; } = typeRegistry;
    public Dictionary<string, Type> Types { get; } = types;
    public Dictionary<Type, HashSet<string>> EventsMap { get; } = eventsMap;
}
