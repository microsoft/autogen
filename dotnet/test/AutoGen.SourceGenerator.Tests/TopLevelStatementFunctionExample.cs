// Copyright (c) Microsoft Corporation. All rights reserved.
// TopLevelStatementFunctionExample.cs

using AutoGen;

public partial class TopLevelStatementFunctionExample
{
    [FunctionAttribute]
    public Task<string> Add(int a, int b)
    {
        return Task.FromResult($"{a + b}");
    }
}
