// Copyright (c) Microsoft Corporation. All rights reserved.
// TopicId.cs

using System.Diagnostics.CodeAnalysis;

namespace Microsoft.AutoGen.Contracts.Python;

public struct TopicId
{
    public string Type { get; }
    public string Source { get; }

    public const string DefaultSource = "default";

    public TopicId(string type, string source = DefaultSource)
    {
        Type = type;
        Source = source;
    }

    public TopicId((string Type, string Source) kvPair) : this(kvPair.Type, kvPair.Source)
    {
    }

    public static TopicId FromStr(string maybeTopicId) => new TopicId(maybeTopicId.ToKVPair(nameof(Type), nameof(Source)));

    public override string ToString() => $"{Type}/{Source}";

    public override bool Equals([NotNullWhen(true)] object? obj)
    {
        if (obj is TopicId other)
        {
            return Type == other.Type && Source == other.Source;
        }

        return false;
    }

    public override int GetHashCode()
    {
        return HashCode.Combine(Type, Source);
    }

    public static explicit operator TopicId(string id) => FromStr(id);

    // TODO: Implement < for wildcard matching (type, *)
    // == => <
    // Type == other.Type => <
    public bool IsWildcardMatch(TopicId other)
    {
        return Type == other.Type;
    }
}

