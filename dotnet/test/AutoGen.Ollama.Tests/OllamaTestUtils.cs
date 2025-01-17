// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaTestUtils.cs

namespace AutoGen.Ollama.Tests;

public static class OllamaTestUtils
{
    public static Tool WeatherTool => new()
    {
        Function = new Function
        {
            Name = "get_current_weather",
            Description = "Get the current weather for a location",
            Parameters = new Parameters
            {
                Properties = new Dictionary<string, Properties>
                {
                    {
                        "location",
                        new Properties
                        {
                            Type = "string", Description = "The location to get the weather for, e.g. San Francisco, CA"
                        }
                    },
                    {
                        "format", new Properties
                        {
                            Type = "string",
                            Description =
                                "The format to return the weather in, e.g. 'celsius' or 'fahrenheit'",
                            Enum = new List<string> {"celsius", "fahrenheit"}
                        }
                    }
                },
                Required = new List<string> { "location", "format" }
            }
        }
    };
}
