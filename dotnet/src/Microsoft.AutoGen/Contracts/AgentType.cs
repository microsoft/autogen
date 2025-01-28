// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentType.cs

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Represents the type of an agent as a string.
/// This is a strongly-typed wrapper around a string, ensuring type safety when working with agent types.
/// </summary>
/// <remarks>
/// This struct is immutable and provides implicit conversion to and from <see cref="string"/>.
/// </remarks>
public struct AgentType
{
    /// <summary>
    /// The string representation of this agent type.
    /// </summary>
    public required string Name;

    /// <summary>
    /// Explicitly converts a <see cref="Type"/> to an <see cref="AgentType"/>.
    /// </summary>
    /// <param name="type">The .NET <see cref="Type"/> to convert.</param>
    /// <returns>An <see cref="AgentType"/> instance with the name of the provided type.</returns>
    public static explicit operator AgentType(Type type) => new AgentType { Name = type.Name };

    /// <summary>
    /// Implicitly converts a <see cref="string"/> to an <see cref="AgentType"/>.
    /// </summary>
    /// <param name="type">The string representation of the agent type.</param>
    /// <returns>An <see cref="AgentType"/> instance with the given name.</returns>
    public static implicit operator AgentType(string type) => new AgentType { Name = type };

    /// <summary>
    /// Implicitly converts an <see cref="AgentType"/> to a <see cref="string"/>.
    /// </summary>
    /// <param name="type">The <see cref="AgentType"/> instance.</param>
    /// <returns>The string representation of the agent type.</returns>
    public static implicit operator string(AgentType type) => type.Name;
}

