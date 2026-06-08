// Copyright (c) Microsoft Corporation. All rights reserved.
// FilescopeNamespaceFunctionExample.cs

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
