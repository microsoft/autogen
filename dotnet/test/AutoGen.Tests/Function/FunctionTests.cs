// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionTests.cs

using System;
using System.ComponentModel;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using ApprovalTests;
using ApprovalTests.Namers;
using ApprovalTests.Reporters;
using AutoGen.OpenAI.Extension;
using FluentAssertions;
using Microsoft.Extensions.AI;
using Xunit;

namespace AutoGen.Tests.Function;

[Trait("Category", "UnitV1")]
public class FunctionTests
{
    private readonly JsonSerializerOptions _jsonSerializerOptions = new() { WriteIndented = true, DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull };
    [Description("get weather")]
    public string GetWeather(string city, string date = "today")
    {
        return $"The weather in {city} is sunny.";
    }

    [Description("get weather from static method")]
    [return: Description("weather information")]
    public static string GetWeatherStatic(string city, string[] date)
    {
        return $"The weather in {city} is sunny.";
    }

    [Description("get weather from async method")]
    public async Task<string> GetWeatherAsync(string city)
    {
        await Task.Delay(100);
        return $"The weather in {city} is sunny.";
    }

    [Description("get weather from async static method")]
    public static async Task<string> GetWeatherAsyncStatic(string city)
    {
        await Task.Delay(100);
        return $"The weather in {city} is sunny.";
    }

    [Fact]
    [UseReporter(typeof(DiffReporter))]
    [UseApprovalSubdirectory("ApprovalTests")]
    public async Task CreateGetWeatherFunctionFromAIFunctionFactoryAsync()
    {
        Delegate[] availableDelegates = [
            GetWeather,
            GetWeatherStatic,
            GetWeatherAsync,
            GetWeatherAsyncStatic,
        ];

        var functionContracts = availableDelegates.Select(function => (FunctionContract)AIFunctionFactory.Create(function)).ToList();

        // Verify the function contracts
        functionContracts.Should().HaveCount(4);

        var openAIToolContracts = functionContracts.Select(f =>
        {
            var tool = f.ToChatTool();

            return new
            {
                tool.Kind,
                tool.FunctionName,
                tool.FunctionDescription,
                FunctionParameters = tool.FunctionParameters.ToObjectFromJson<object>(),
            };
        });

        var json = JsonSerializer.Serialize(openAIToolContracts, _jsonSerializerOptions);
        Approvals.Verify(json);
    }
}
