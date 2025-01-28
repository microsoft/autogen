// Copyright (c) Microsoft Corporation. All rights reserved.
// TopicId.cs

using System.Diagnostics.CodeAnalysis;

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Represents a topic identifier that defines the scope of a broadcast message.
/// The agent runtime implements a publish-subscribe model through its broadcast API,
/// where messages must be published with a specific topic.
///
/// See the Python equivalent:
/// <see href="https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#type">CloudEvents Type Specification</see>.
/// </summary>
public struct TopicId
{
    /// <summary>
    /// Gets the type of the event that this <see cref="TopicId"/> represents.
    /// This adheres to the CloudEvents specification.
    ///
    /// Must match the pattern: <c>^[\w\-\.\:\=]+$</c>.
    ///
    /// Learn more here:
    /// <see href="https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#type">CloudEvents Type</see>.
    /// </summary>
    public string Type { get; }

    /// <summary>
    /// Gets the source that identifies the context in which an event happened.
    /// This adheres to the CloudEvents specification.
    ///
    /// Learn more here:
    /// <see href="https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#source-1">CloudEvents Source</see>.
    /// </summary>
    public string Source { get; }

    /// <summary>
    /// The default source value used when no source is explicitly provided.
    /// </summary>
    public const string DefaultSource = "default";

    /// <summary>
    /// Initializes a new instance of the <see cref="TopicId"/> struct.
    /// </summary>
    /// <param name="type">The type of the topic.</param>
    /// <param name="source">The source of the event. Defaults to <see cref="DefaultSource"/> if not specified.</param>
    public TopicId(string type, string source = DefaultSource)
    {
        Type = type;
        Source = source;
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="TopicId"/> struct from a tuple.
    /// </summary>
    /// <param name="kvPair">A tuple containing the topic type and source.</param>
    public TopicId((string Type, string Source) kvPair) : this(kvPair.Type, kvPair.Source)
    {
    }

    /// <summary>
    /// Converts a string in the format "type/source" into a <see cref="TopicId"/>.
    /// </summary>
    /// <param name="maybeTopicId">The topic ID string.</param>
    /// <returns>An instance of <see cref="TopicId"/>.</returns>
    /// <exception cref="FormatException">Thrown when the string is not in the valid "type/source" format.</exception>
    public static TopicId FromStr(string maybeTopicId) => new TopicId(maybeTopicId.ToKVPair(nameof(Type), nameof(Source)));

    /// <summary>
    /// Returns the string representation of the <see cref="TopicId"/>.
    /// </summary>
    /// <returns>A string in the format "type/source".</returns>
    public override string ToString() => $"{Type}/{Source}";

    /// <summary>
    /// Determines whether the specified object is equal to the current <see cref="TopicId"/>.
    /// </summary>
    /// <param name="obj">The object to compare with the current instance.</param>
    /// <returns><c>true</c> if the specified object is equal to the current <see cref="TopicId"/>; otherwise, <c>false</c>.</returns>
    public override bool Equals([NotNullWhen(true)] object? obj)
    {
        if (obj is TopicId other)
        {
            return Type == other.Type && Source == other.Source;
        }

        return false;
    }

    /// <summary>
    /// Returns a hash code for this <see cref="TopicId"/>.
    /// </summary>
    /// <returns>A hash code for the current instance.</returns>
    public override int GetHashCode()
    {
        return HashCode.Combine(Type, Source);
    }

    /// <summary>
    /// Explicitly converts a string to a <see cref="TopicId"/>.
    /// </summary>
    /// <param name="id">The string representation of a topic ID.</param>
    /// <returns>An instance of <see cref="TopicId"/>.</returns>
    public static explicit operator TopicId(string id) => FromStr(id);

    // TODO: Implement < for wildcard matching (type, *)
    // == => <
    // Type == other.Type => <
    /// <summary>
    /// Determines whether the given <see cref="TopicId"/> matches another topic.
    /// </summary>
    /// <param name="other">The topic ID to compare against.</param>
    /// <returns>
    /// <c>true</c> if the topic types are equal; otherwise, <c>false</c>.
    /// </returns>
    public bool IsWildcardMatch(TopicId other)
    {
        return Type == other.Type;
    }
}

