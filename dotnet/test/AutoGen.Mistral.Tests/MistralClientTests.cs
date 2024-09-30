// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralClientTests.cs

using System.Text.Json;
using System.Text.Json.Serialization;
using AutoGen.Core;
using AutoGen.Mistral.Extension;
using AutoGen.Tests;
using FluentAssertions;

namespace AutoGen.Mistral.Tests;

public partial class MistralClientTests
{
    [Function]
    public async Task<string> GetWeather(string city)
    {
        return $"The weather in {city} is sunny.";
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralClientChatCompletionTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);

        var systemMessage = new ChatMessage(ChatMessage.RoleEnum.System, "You are a helpful assistant.");
        var userMessage = new ChatMessage(ChatMessage.RoleEnum.User, "What is the weather like today?");

        var request = new ChatCompletionRequest(
            model: "open-mistral-7b",
            messages: new List<ChatMessage> { systemMessage, userMessage },
            temperature: 0);

        var response = await client.CreateChatCompletionsAsync(request);

        response.Choices!.Count().Should().Be(1);
        response.Choices!.First().Message!.Content.Should().NotBeNullOrEmpty();
        response.Choices!.First().Message!.Role.Should().Be(ChatMessage.RoleEnum.Assistant);
        response.Usage!.TotalTokens.Should().BeGreaterThan(0);
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralClientStreamingChatCompletionTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);

        var systemMessage = new ChatMessage(ChatMessage.RoleEnum.System, "You are a helpful assistant.");
        var userMessage = new ChatMessage(ChatMessage.RoleEnum.User, "What is the weather like today?");

        var request = new ChatCompletionRequest(
            model: "open-mistral-7b",
            messages: new List<ChatMessage> { systemMessage, userMessage },
            temperature: 0);

        var response = client.StreamingChatCompletionsAsync(request);
        var results = new List<ChatCompletionResponse>();

        await foreach (var item in response)
        {
            results.Add(item);
            item.VarObject.Should().Be("chat.completion.chunk");
        }

        results.Count.Should().BeGreaterThan(0);

        // merge result
        var finalResult = results.First();
        foreach (var result in results)
        {
            if (finalResult.Choices!.First().Message is null)
            {
                finalResult.Choices!.First().Message = result.Choices!.First().Delta;
            }
            else
            {
                finalResult.Choices!.First().Message!.Content += result.Choices!.First().Delta!.Content;
            }

            // the usage information will be included in the last result
            if (result.Usage != null)
            {
                finalResult.Usage = result.Usage;
            }
        }
        finalResult.Choices!.First().Message!.Content.Should().NotBeNullOrEmpty();
        finalResult.Choices!.First().Message!.Role.Should().Be(ChatMessage.RoleEnum.Assistant);
        finalResult.Usage!.TotalTokens.Should().BeGreaterThan(0);
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralClientStreamingChatJsonModeCompletionTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);

        var systemMessage = new ChatMessage(ChatMessage.RoleEnum.System, "You are a helpful assistant that convert input to json object");
        var userMessage = new ChatMessage(ChatMessage.RoleEnum.User, "name: John, age: 41, email: g123456@gmail.com");

        var request = new ChatCompletionRequest(
            model: "open-mistral-7b",
            messages: new List<ChatMessage> { systemMessage, userMessage },
            temperature: 0)
        {
            ResponseFormat = new ResponseFormat { ResponseFormatType = "json_object" },
        };

        var response = client.StreamingChatCompletionsAsync(request);
        var results = new List<ChatCompletionResponse>();

        await foreach (var item in response)
        {
            results.Add(item);
            item.VarObject.Should().Be("chat.completion.chunk");
        }

        results.Count.Should().BeGreaterThan(0);

        // merge result
        var finalResult = results.First();
        foreach (var result in results)
        {
            if (finalResult.Choices!.First().Message is null)
            {
                finalResult.Choices!.First().Message = result.Choices!.First().Delta;
            }
            else
            {
                finalResult.Choices!.First().Message!.Content += result.Choices!.First().Delta!.Content;
            }

            // the usage information will be included in the last result
            if (result.Usage != null)
            {
                finalResult.Usage = result.Usage;
            }
        }

        finalResult.Choices!.First().Message!.Content.Should().NotBeNullOrEmpty();
        finalResult.Choices!.First().Message!.Role.Should().Be(ChatMessage.RoleEnum.Assistant);
        finalResult.Usage!.TotalTokens.Should().BeGreaterThan(0);
        var responseContent = finalResult.Choices!.First().Message!.Content ?? throw new InvalidOperationException("Response content is null.");
        var person = JsonSerializer.Deserialize<Person>(responseContent);
        person.Should().NotBeNull();

        person!.Name.Should().Be("John");
        person!.Age.Should().Be(41);
        person!.Email.Should().Be("g123456@gmail.com");
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralClientJsonModeTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);

        var systemMessage = new ChatMessage(ChatMessage.RoleEnum.System, "You are a helpful assistant that convert input to json object");
        var userMessage = new ChatMessage(ChatMessage.RoleEnum.User, "name: John, age: 41, email: g123456@gmail.com");

        var request = new ChatCompletionRequest(
            model: "open-mistral-7b",
            messages: new List<ChatMessage> { systemMessage, userMessage },
            temperature: 0)
        {
            ResponseFormat = new ResponseFormat { ResponseFormatType = "json_object" },
        };

        var response = await client.CreateChatCompletionsAsync(request);

        response.Choices!.Count().Should().Be(1);
        response.Choices!.First().Message!.Content.Should().NotBeNullOrEmpty();
        response.Choices!.First().Message!.Role.Should().Be(ChatMessage.RoleEnum.Assistant);
        response.Usage!.TotalTokens.Should().BeGreaterThan(0);

        // check if the response is a valid json object
        var responseContent = response.Choices!.First().Message!.Content ?? throw new InvalidOperationException("Response content is null.");
        var person = JsonSerializer.Deserialize<Person>(responseContent);
        person.Should().NotBeNull();

        person!.Name.Should().Be("John");
        person!.Age.Should().Be(41);
        person!.Email.Should().Be("g123456@gmail.com");
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralClientFunctionCallTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        using var client = new MistralClient(apiKey: apiKey);

        var getWeatherFunctionContract = this.GetWeatherFunctionContract;
        var functionDefinition = getWeatherFunctionContract.ToMistralFunctionDefinition();

        var systemMessage = new ChatMessage(ChatMessage.RoleEnum.System, "You are a helpful assistant.");
        var userMessage = new ChatMessage(ChatMessage.RoleEnum.User, "What is the weather in Seattle?");

        var request = new ChatCompletionRequest(
            model: "mistral-small-latest", // only large or small latest models support function calls
            messages: new List<ChatMessage> { systemMessage, userMessage },
            temperature: 0)
        {
            Tools = [new FunctionTool(functionDefinition)],
            ToolChoice = ToolChoiceEnum.Any,
        };

        var response = await client.CreateChatCompletionsAsync(request);

        response.Choices!.Count().Should().Be(1);
        response.Choices!.First().Message!.Content.Should().BeNullOrEmpty();
        response.Choices!.First().FinishReason.Should().Be(Choice.FinishReasonEnum.ToolCalls);
        response.Choices!.First().Message!.ToolCalls!.Count.Should().Be(1);
        response.Choices!.First().Message!.ToolCalls!.First().Function.Name.Should().Be("GetWeather");
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralClientStreamingFunctionCallTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        using var client = new MistralClient(apiKey: apiKey);

        var getWeatherFunctionContract = this.GetWeatherFunctionContract;
        var functionDefinition = getWeatherFunctionContract.ToMistralFunctionDefinition();

        var systemMessage = new ChatMessage(ChatMessage.RoleEnum.System, "You are a helpful assistant.");
        var userMessage = new ChatMessage(ChatMessage.RoleEnum.User, "What is the weather in Seattle?");

        var request = new ChatCompletionRequest(
            model: "mistral-small-latest",
            messages: new List<ChatMessage> { systemMessage, userMessage },
            temperature: 0)
        {
            Tools = [new FunctionTool(functionDefinition)],
            ToolChoice = ToolChoiceEnum.Any,
        };

        var response = client.StreamingChatCompletionsAsync(request);

        var results = new List<ChatCompletionResponse>();
        await foreach (var item in response)
        {
            results.Add(item);
            item.VarObject.Should().Be("chat.completion.chunk");
        }

        // merge result
        var finalResult = results.First();
        var lastResult = results.Last();
        lastResult.Choices!.First().FinishReason.Should().Be(Choice.FinishReasonEnum.ToolCalls);

        foreach (var result in results)
        {
            if (finalResult.Choices!.First().Message is null)
            {
                finalResult.Choices!.First().Message = result.Choices!.First().Delta;
                finalResult.Choices!.First().Message!.ToolCalls = [];
            }
            else
            {
                finalResult.Choices!.First().Message!.ToolCalls = finalResult.Choices!.First().Message!.ToolCalls!.Concat(result.Choices!.First().Delta!.ToolCalls!).ToList();
            }

            // the usage information will be included in the last result
            if (result.Usage != null)
            {
                finalResult.Usage = result.Usage;
            }
        }

        finalResult.Choices!.First().Message!.Content.Should().BeNullOrEmpty();
        finalResult.Choices!.First().Message!.ToolCalls!.Count.Should().BeGreaterThan(0);
        finalResult.Usage!.TotalTokens.Should().BeGreaterThan(0);
        finalResult.Choices!.First().Message!.ToolCalls!.First().Function.Name.Should().Be("GetWeather");
    }
}
public class Person
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("age")]
    public int Age { get; set; }

    [JsonPropertyName("email")]
    public string Email { get; set; } = string.Empty;
}
