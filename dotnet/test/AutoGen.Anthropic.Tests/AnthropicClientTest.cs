using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using AutoGen.Anthropic.DTO;
using AutoGen.Anthropic.Utils;
using AutoGen.Tests;
using FluentAssertions;
using Xunit;

namespace AutoGen.Anthropic;

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
        request.SystemMessage = "You are a helpful assistant that convert input to json object";
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
                sb.Append(result.Delta.Text);
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
