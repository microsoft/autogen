// Copyright (c) Microsoft Corporation. All rights reserved.
// ICodeExecutor.cs

namespace Microsoft.AutoGen.Abstractions;

// TODO: Should these be classes?
public struct CodeBlock
{
    public required string Code { get; set; }
    public required string Language { get; set; } // TODO: We should raise this into the routing type, somehow
}

public struct CodeResult
{
    public required int ExitCode { get; set; }
    public required string Output { get; set; }
}

public interface ICodeExecutor
{
    ValueTask<CodeResult> ExecuteCodeBlocksAsync(IEnumerable<CodeBlock> codeBlocks, CancellationToken cancellationToken = default);
    ValueTask RestartAsync();
}
