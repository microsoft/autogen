// Copyright (c) Microsoft Corporation. All rights reserved.
// IProcessIO.cs

namespace Microsoft.AutoGen.Agents;

/// <summary>
/// Default Interface methods for processing input and output shared by IOAgents that should be implemented in your agent
/// </summary>
public interface IProcessIO
{
    /// <summary>
    /// Implement this method in your agent to process the input
    /// </summary>
    /// <param name="message"></param>
    /// <returns>Task</returns>
    static Task ProcessOutputAsync(string message) { return Task.CompletedTask; }
    /// <summary>
    /// Implement this method in your agent to process the output
    /// </summary>
    /// <param name="message"></param>
    /// <returns>Task</returns>
    static Task<string> ProcessInputAsync(string message) { return Task.FromResult(message); }
}
