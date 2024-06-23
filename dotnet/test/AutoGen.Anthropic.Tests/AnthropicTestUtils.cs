// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicTestUtils.cs

using AutoGen.Anthropic.DTO;

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

    public static Tool WeatherTool
    {
        get
        {
            return new Tool
            {
                Name = "WeatherReport",
                Description = "Get the current weather",
                InputSchema = new InputSchema
                {
                    Type = "object",
                    Properties = new Dictionary<string, SchemaProperty>
                    {
                        { "city", new SchemaProperty {Type = "string", Description = "The name of the city"} },
                        { "date", new SchemaProperty {Type = "string", Description = "date of the day"} }
                    }
                }
            };
        }
    }
}
