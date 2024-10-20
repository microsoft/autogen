// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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

    [Function]
    public async Task<string> GetMovies(string location, string description)
    {
        var movies = new List<string> { "Barbie", "Spiderman", "Batman" };

        return await Task.FromResult($"Movies playing in {location} based on {description} are: {string.Join(", ", movies)}");
    }
}
