// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicClientTest.cs

using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using AutoGen.Anthropic.DTO;
using AutoGen.Anthropic.Utils;
using AutoGen.Tests;
using FluentAssertions;
using Xunit;

namespace AutoGen.Anthropic.Tests;

public class AnthropicClientTests
{
    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicClientChatCompletionTestAsync()
    {
        var anthropicClient = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var request = new ChatCompletionRequest();
        request.Model = AnthropicConstants.Claude3Haiku;
        request.Stream = false;
        request.MaxTokens = 100;
        request.Messages = new List<ChatMessage>() { new ChatMessage("user", "Hello world") };
        ChatCompletionResponse response = await anthropicClient.CreateChatCompletionsAsync(request, CancellationToken.None);

        Assert.NotNull(response);
        Assert.NotNull(response.Content);
        Assert.NotEmpty(response.Content);
        response.Content.Count.Should().Be(1);
        response.Content.First().Should().BeOfType<TextContent>();
        var textContent = (TextContent)response.Content.First();
        Assert.Equal("text", textContent.Type);
        Assert.NotNull(response.Usage);
        response.Usage.OutputTokens.Should().BeGreaterThan(0);
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicClientStreamingChatCompletionTestAsync()
    {
        var anthropicClient = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var request = new ChatCompletionRequest();
        request.Model = AnthropicConstants.Claude3Haiku;
        request.Stream = true;
        request.MaxTokens = 500;
        request.SystemMessage =
        [
            SystemMessage.CreateSystemMessage(
            "You are a helpful assistant that convert input to json object, use JSON format.")
        ];

        request.Messages = new List<ChatMessage>()
        {
            new("user", "name: John, age: 41, email: g123456@gmail.com")
        };

        var response = anthropicClient.StreamingChatCompletionsAsync(request, CancellationToken.None);
        var results = await response.ToListAsync();
        results.Count.Should().BeGreaterThan(0);

        // Merge the chunks.
        StringBuilder sb = new();
        foreach (ChatCompletionResponse result in results)
        {
            if (result.Delta is not null && !string.IsNullOrEmpty(result.Delta.Text))
            {
                sb.Append(result.Delta.Text);
            }
        }

        string resultContent = sb.ToString();
        Assert.NotNull(resultContent);

        var person = JsonSerializer.Deserialize<Person>(resultContent);
        Assert.NotNull(person);
        person.Name.Should().Be("John");
        person.Age.Should().Be(41);
        person.Email.Should().Be("g123456@gmail.com");
        Assert.NotNull(results.First().streamingMessage);
        results.First().streamingMessage!.Role.Should().Be("assistant");
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicClientImageChatCompletionTestAsync()
    {
        var anthropicClient = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var request = new ChatCompletionRequest();
        request.Model = AnthropicConstants.Claude3Haiku;
        request.Stream = false;
        request.MaxTokens = 100;
        request.SystemMessage =
        [
            SystemMessage.CreateSystemMessage(
                "You are a LLM that is suppose to describe the content of the image. Give me a description of the provided image."),
        ];

        var base64Image = await AnthropicTestUtils.Base64FromImageAsync("square.png");
        var messages = new List<ChatMessage>
        {
            new("user",
            [
                new ImageContent { Source = new ImageSource {MediaType = "image/png", Data = base64Image} }
            ])
        };

        request.Messages = messages;

        var response = await anthropicClient.CreateChatCompletionsAsync(request, CancellationToken.None);

        Assert.NotNull(response);
        Assert.NotNull(response.Content);
        Assert.NotEmpty(response.Content);
        response.Content.Count.Should().Be(1);
        response.Content.First().Should().BeOfType<TextContent>();
        var textContent = (TextContent)response.Content.First();
        Assert.Equal("text", textContent.Type);
        Assert.NotNull(response.Usage);
        response.Usage.OutputTokens.Should().BeGreaterThan(0);
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicClientTestToolsAsync()
    {
        var anthropicClient = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var request = new ChatCompletionRequest();
        request.Model = AnthropicConstants.Claude3Haiku;
        request.Stream = false;
        request.MaxTokens = 100;
        request.Messages = new List<ChatMessage>() { new("user", "Use the stock price tool to look for MSFT. Your response should only be the tool.") };
        request.Tools = new List<Tool>() { AnthropicTestUtils.StockTool };

        ChatCompletionResponse response =
            await anthropicClient.CreateChatCompletionsAsync(request, CancellationToken.None);

        Assert.NotNull(response.Content);
        Assert.True(response.Content.First() is ToolUseContent);
        ToolUseContent toolUseContent = ((ToolUseContent)response.Content.First());
        Assert.Equal("get_stock_price", toolUseContent.Name);
        Assert.NotNull(toolUseContent.Input);
        Assert.True(toolUseContent.Input is JsonNode);
        JsonNode jsonNode = toolUseContent.Input;
        Assert.Equal("{\"ticker\":\"MSFT\"}", jsonNode.ToJsonString());
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicClientTestToolChoiceAsync()
    {
        var anthropicClient = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var request = new ChatCompletionRequest();
        request.Model = AnthropicConstants.Claude3Haiku;
        request.Stream = false;
        request.MaxTokens = 100;
        request.Messages = new List<ChatMessage>() { new("user", "What is the weather today? Your response should only be the tool.") };
        request.Tools = new List<Tool>() { AnthropicTestUtils.StockTool, AnthropicTestUtils.WeatherTool };

        // Force to use get_stock_price even though the prompt is about weather 
        request.ToolChoice = ToolChoice.ToolUse("get_stock_price");

        ChatCompletionResponse response =
            await anthropicClient.CreateChatCompletionsAsync(request, CancellationToken.None);

        Assert.NotNull(response.Content);
        Assert.True(response.Content.First() is ToolUseContent);
        ToolUseContent toolUseContent = ((ToolUseContent)response.Content.First());
        Assert.Equal("get_stock_price", toolUseContent.Name);
        Assert.NotNull(toolUseContent.Input);
        Assert.True(toolUseContent.Input is JsonNode);
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicClientChatCompletionCacheControlTestAsync()
    {
        var anthropicClient = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var request = new ChatCompletionRequest();
        request.Model = AnthropicConstants.Claude35Sonnet;
        request.Stream = false;
        request.MaxTokens = 100;

        request.SystemMessage =
        [
            SystemMessage.CreateSystemMessageWithCacheControl(
                $"You are an LLM that is great at remembering stories {AnthropicTestUtils.LongStory}"),
        ];

        request.Messages =
        [
            new ChatMessage("user", "What should i know about Bob?")
        ];

        var response = await anthropicClient.CreateChatCompletionsAsync(request, CancellationToken.None);
        response.Usage.Should().NotBeNull();

        // There's no way to clear the cache. Running the assert frequently may cause this to fail because the cache is already been created 
        // response.Usage!.CreationInputTokens.Should().BeGreaterThan(0);
        // The cache reduces the input tokens. We expect the input tokens to be less the large system prompt and only the user message
        response.Usage!.InputTokens.Should().BeLessThan(20);

        request.Messages =
        [
            new ChatMessage("user", "Summarize the story of bob")
        ];

        response = await anthropicClient.CreateChatCompletionsAsync(request, CancellationToken.None);
        response.Usage.Should().NotBeNull();
        response.Usage!.CacheReadInputTokens.Should().BeGreaterThan(0);
        response.Usage!.InputTokens.Should().BeLessThan(20);

        // Should not use the cache
        request.SystemMessage =
        [
            SystemMessage.CreateSystemMessage("You are a helpful assistant.")
        ];

        request.Messages =
        [
            new ChatMessage("user", "What are some text editors I could use to write C#?")
        ];

        response = await anthropicClient.CreateChatCompletionsAsync(request, CancellationToken.None);
        response.Usage!.CacheReadInputTokens.Should().Be(0);
    }

    private sealed class Person
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("age")]
        public int Age { get; set; }

        [JsonPropertyName("email")]
        public string Email { get; set; } = string.Empty;
    }
}
