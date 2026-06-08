// Copyright (c) Microsoft Corporation. All rights reserved.
// InProcessRuntimeExtensions.cs
namespace Microsoft.AutoGen.Core.Tests;

public static class InProcessRuntimeExtensions
{
    public static async ValueTask RunUntilIdleAndRestartAsync(this InProcessRuntime this_)
    {
        await this_.RunUntilIdleAsync();
        await this_.StartAsync();
    }
}
