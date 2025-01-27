// Copyright (c) Microsoft Corporation. All rights reserved.
// PythonInterfaces.cs

namespace Microsoft.AutoGen.Contracts.Python;

/// <summary>
/// Represents metadata associated with an agent, including its type, unique key, and description.
/// </summary>
public struct AgentMetadata(string type, string key, string description)
{
    /// <summary>
    /// An identifier that associates an agent with a specific factory function.
    /// Strings may only be composed of alphanumeric letters (a-z, 0-9), or underscores (_).
    /// </summary>
    public string Type { get; set; } = type;

    /// <summary>
    /// A unique key identifying the agent instance.
    /// Strings may only be composed of alphanumeric letters (a-z, 0-9), or underscores (_).
    /// </summary>
    public string Key { get; set; } = key;

    /// <summary>
    /// A brief description of the agent's purpose or functionality.
    /// </summary>    
    public string Description { get; set; } = description;
}

