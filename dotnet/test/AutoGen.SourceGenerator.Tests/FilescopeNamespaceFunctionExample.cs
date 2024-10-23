// Copyright (c) Microsoft. All rights reserved.

using AutoGen.Core;

namespace AutoGen.SourceGenerator.Tests;
public partial class FilescopeNamespaceFunctionExample
{
    [Function]
    public Task<string> Add(int a, int b)
    {
        return Task.FromResult($"{a + b}");
    }
}
