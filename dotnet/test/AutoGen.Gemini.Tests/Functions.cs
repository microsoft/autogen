// Copyright (c) Microsoft Corporation. All rights reserved.
// Functions.cs

using AutoGen.Core;

namespace AutoGen.Gemini.Tests;

public partial class Functions
{
    /// <summary>
    /// Get weather for a city.
    /// </summary>
    /// <param name="city">city</param>
    /// <returns>weather</returns>
    [Function]
    public async Task<string> GetWeatherAsync(string city)
    {
        return await Task.FromResult($"The weather in {city} is sunny.");
    }
}
