// Copyright (c) Microsoft Corporation. All rights reserved.
// ICodeExecutor.cs

namespace Microsoft.AutoGen.Abstractions;

/// <summary>
/// A code block extracted from an agent message.
/// </summary>
public struct CodeBlock
{
    public required string Code { get; set; }
    public required string Language { get; set; } // TODO: We should raise this into the routing type, somehow
}

/// <summary>
/// Result of code execution.
/// </summary>
public struct CodeResult
{
    public required int ExitCode { get; set; }
    public required string Output { get; set; }
}

/// <summary>
/// Executes code blocks and returns the result.
/// </summary>
public interface ICodeExecutor
{
    /// <summary>
    /// Execute code blocks and return the result.
    /// </summary>
    /// <param name="codeBlocks">The code blocks to execute.</param>
    /// <param name="cancellationToken">A cancellation token to cancel the execution.</param>
    /// <returns>The result of code execution.</returns>
    ValueTask<CodeResult> ExecuteCodeBlocksAsync(IEnumerable<CodeBlock> codeBlocks, CancellationToken cancellationToken = default);

    /// <summary>
    /// Restarts the code executor.
    /// </summary>
    /// <returns>
    /// A ValueTask that represents the possibly asynchronous operation.
    /// </returns>
    ValueTask RestartAsync();
}
