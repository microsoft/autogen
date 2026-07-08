// Copyright (c) Microsoft Corporation. All rights reserved.
// TopLevelStatementFunctionExample.cs

using AutoGen.Core;

public partial class TopLevelStatementFunctionExample
{
    [Function]
    public Task<string> Add(int a, int b)
    {
        return Task.FromResult($"{a + b}");
    }
}
