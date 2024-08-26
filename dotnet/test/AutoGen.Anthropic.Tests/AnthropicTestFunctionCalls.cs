// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicTestFunctionCalls.cs

using System.Text.Json;
using System.Text.Json.Serialization;
using AutoGen.Core;

namespace AutoGen.Anthropic.Tests;

public partial class AnthropicTestFunctionCalls
{
    private class GetWeatherSchema
    {
        [JsonPropertyName("city")]
        public string? City { get; set; }

        [JsonPropertyName("date")]
        public string? Date { get; set; }
    }

    /// <summary>
    /// Get weather report
    /// </summary>
    /// <param name="city">city</param>
    /// <param name="date">date</param>
    [Function]
    public async Task<string> WeatherReport(string city, string date)
    {
        return $"Weather report for {city} on {date} is sunny";
    }

    public Task<string> GetWeatherReportWrapper(string arguments)
    {
        var schema = JsonSerializer.Deserialize<GetWeatherSchema>(
            arguments,
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });

        return WeatherReport(schema?.City ?? string.Empty, schema?.Date ?? string.Empty);
    }
}
