// Copyright (c) Microsoft Corporation. All rights reserved.
// PythonInterfaces.cs

using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;

namespace Microsoft.AutoGen.Contracts.Python;

[DebuggerDisplay($"AgentId(type=\"{nameof(Type)}\", key=\"{nameof(Key)}\")")]
public struct AgentId
{
    public string Type;
    public string Key;

    public AgentId(string type, string key)
    {
        Type = type;
        Key = key;
    }

    public AgentId((string Type, string Key) kvPair) : this(kvPair.Type, kvPair.Key)
    {
    }

    public AgentId(AgentType type, string key) : this(type.Name, key)
    {
    }

    public static AgentId FromStr(string maybeAgentId) => new AgentId(maybeAgentId.ToKVPair(nameof(Type), nameof(Key)));

    public override string ToString() => $"{Type}/{Key}";

    public override bool Equals([NotNullWhen(true)] object? obj)
    {
        if (obj is AgentId other)
        {
            return Type == other.Type && Key == other.Key;
        }

        return false;
    }

    public override int GetHashCode()
    {
        return HashCode.Combine(Type, Key);
    }

    public static explicit operator AgentId(string id) => FromStr(id);
}

