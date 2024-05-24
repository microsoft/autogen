// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicTestUtils.cs

namespace AutoGen.Anthropic;

public static class AnthropicTestUtils
{
    public static string ApiKey => Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY") ??
                             throw new Exception("Please set ANTHROPIC_API_KEY environment variable.");
}
