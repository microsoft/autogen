// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

namespace AutoGen.Anthropic.Samples;

internal static class Program
{
    public static async Task Main(string[] _)
    {
        await Anthropic_Agent_With_Prompt_Caching.RunAsync();
    }
}
