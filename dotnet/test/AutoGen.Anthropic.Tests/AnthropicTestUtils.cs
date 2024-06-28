// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicTestUtils.cs

namespace AutoGen.Anthropic.Tests;

public static class AnthropicTestUtils
{
    public static string ApiKey => Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY") ??
                             throw new Exception("Please set ANTHROPIC_API_KEY environment variable.");

    public static async Task<string> Base64FromImageAsync(string imageName)
    {
        return Convert.ToBase64String(
            await File.ReadAllBytesAsync(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "images", imageName)));
    }
}
