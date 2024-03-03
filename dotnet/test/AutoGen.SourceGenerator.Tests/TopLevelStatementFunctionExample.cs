// Copyright (c) Microsoft Corporation. All rights reserved.
// TopLevelStatementFunctionExample.cs

public partial class TopLevelStatementFunctionExample
{
    [Function]
    public Task<string> Add(int a, int b)
    {
        return Task.FromResult($"{a + b}");
    }
}
