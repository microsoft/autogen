// Copyright (c) Microsoft Corporation. All rights reserved.
// TopLevelStatementFunctionExample.cs

namespace AutoGen.SourceGenerator.Tests;
public partial class FilescopeNamespaceFunctionExample
{
    [Function]
    public Task<string> Add(int a, int b)
    {
        return Task.FromResult($"{a + b}");
    }
}
