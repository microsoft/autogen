// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandleExtensions.cs

using System.Reflection;

namespace Microsoft.AutoGen.Core;

/// <summary>
/// Provides extension methods for types implementing the IHandle interface.
/// </summary>
public static class IHandleExtensions
{
    /// <summary>
    /// Gets all the handler methods from the interfaces implemented by the specified type.
    /// </summary>
    /// <param name="type">The type to get the handler methods from.</param>
    /// <returns>An array of MethodInfo objects representing the handler methods.</returns>
    public static MethodInfo[] GetHandlers(this Type type)
    {
        var handlers = type.GetInterfaces().Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IHandle<>));
        return handlers.SelectMany(h => h.GetMethods().Where(m => m.Name == "Handle")).ToArray();
    }

    /// <summary>
    /// Gets a lookup table of handler methods from the interfaces implemented by the specified type.
    /// </summary>
    /// <param name="type">The type to get the handler methods from.</param>
    /// <returns>A dictionary where the key is the generic type and the value is the MethodInfo of the handler method.</returns>
    public static Dictionary<Type, MethodInfo> GetHandlersLookupTable(this Type type)
    {
        var handlers = type.GetHandlers();
        return handlers.ToDictionary(h =>
        {
            var generic = h.DeclaringType!.GetGenericArguments();
            return generic[0];
        });
    }
}
