// Copyright (c) Microsoft. All rights reserved.

using AutoGen.Core;

public partial class TopLevelStatementFunctionExample
{
    [Function]
    public Task<string> Add(int a, int b)
    {
        return Task.FromResult($"{a + b}");
    }
}
