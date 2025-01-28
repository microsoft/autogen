// Copyright (c) Microsoft Corporation. All rights reserved.
// PythonInterfaces.cs

using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;

namespace Microsoft.AutoGen.Contracts.Python;

/// <summary>
/// Agent ID uniquely identifies an agent instance within an agent runtime, including a distributed runtime.
/// It serves as the "address" of the agent instance for receiving messages.
/// </summary>
/// See the Python equivalent: 
/// <see href="https://microsoft.github.io/autogen/stable/reference/python/autogen_core.html#autogen_core.AgentId">AgentId in AutoGen (Python)</see>.
/// </remarks>
[DebuggerDisplay($"AgentId(type=\"{nameof(Type)}\", key=\"{nameof(Key)}\")")]
public struct AgentId
{
    /// <summary>
    /// An identifier that associates an agent with a specific factory function.  
    /// Strings may only be composed of alphanumeric letters (a-z) and (0-9), or underscores (_).
    /// </summary>
    public string Type;

    /// <summary>
    /// Agent instance identifier.  
    /// Strings may only be composed of alphanumeric letters (a-z) and (0-9), or underscores (_).
    /// </summary>
    public string Key;

    /// <summary>
    /// Initializes a new instance of the <see cref="AgentId"/> struct.
    /// </summary>
    /// <param name="type">The agent type.</param>
    /// <param name="key">Agent instance identifier.</param>
    public AgentId(string type, string key)
    {
        Type = type;
        Key = key;
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="AgentId"/> struct from a tuple.
    /// </summary>
    /// <param name="kvPair">A tuple containing the agent type and key.</param>
    public AgentId((string Type, string Key) kvPair) : this(kvPair.Type, kvPair.Key)
    {
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="AgentId"/> struct from an <see cref="AgentType"/>.
    /// </summary>
    /// <param name="type">The agent type.</param>
    /// <param name="key">Agent instance identifier.</param>
    public AgentId(AgentType type, string key) : this(type.Name, key)
    {
    }

    /// <summary>
    /// Convert a string of the format "type/key" into an <see cref="AgentId"/>.
    /// </summary>
    /// <param name="maybeAgentId">The agent ID string.</param>
    /// <returns>An instance of <see cref="AgentId"/>.</returns>
    public static AgentId FromStr(string maybeAgentId) => new AgentId(maybeAgentId.ToKVPair(nameof(Type), nameof(Key)));

    /// <summary>
    /// Returns the string representation of the <see cref="AgentId"/>.
    /// </summary>
    /// <returns>A string in the format "type/key".</returns>
    public override string ToString() => $"{Type}/{Key}";

    /// <summary>
    /// Determines whether the specified object is equal to the current <see cref="AgentId"/>.
    /// </summary>
    /// <param name="obj">The object to compare with the current instance.</param>
    /// <returns><c>true</c> if the specified object is equal to the current <see cref="AgentId"/>; otherwise, <c>false</c>.</returns>
    public override bool Equals([NotNullWhen(true)] object? obj)
    {
        if (obj is AgentId other)
        {
            return Type == other.Type && Key == other.Key;
        }

        return false;
    }

    /// <summary>
    /// Returns a hash code for this <see cref="AgentId"/>.
    /// </summary>
    /// <returns>A hash code for the current instance.</returns>
    public override int GetHashCode()
    {
        return HashCode.Combine(Type, Key);
    }

    /// <summary>
    /// Explicitly converts a string to an <see cref="AgentId"/>.
    /// </summary>
    /// <param name="id">The string representation of an agent ID.</param>
    /// <returns>An instance of <see cref="AgentId"/>.</returns>
    public static explicit operator AgentId(string id) => FromStr(id);
}

