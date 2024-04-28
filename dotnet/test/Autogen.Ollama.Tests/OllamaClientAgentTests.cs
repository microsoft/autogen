// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaClientAgentTests.cs

using System.Text.Json;
using AutoGen.Core;
using FluentAssertions;

namespace Autogen.Ollama.Tests;

public class OllamaClientAgentTests
{
    private readonly OllamaClientAgent _ollamaClientAgent;
    private readonly string _host = "http://localhost:11434";

    public OllamaClientAgentTests()
    {
        var httpClient = new HttpClient
        {
            BaseAddress = new Uri(_host),
            Timeout = TimeSpan.FromSeconds(250)
        };
        _ollamaClientAgent = new OllamaClientAgent(httpClient, "TestAgent", "mixtral:latest");
    }

    [Fact]
    public async Task GenerateReplyAsync_ReturnsValidMessage_WhenCalled()
    {
        var messages = new IMessage[] { new TextMessage(Role.User, "Hello") };
        IMessage result = await _ollamaClientAgent.GenerateReplyAsync(messages);

        result.Should().NotBeNull();
        result.Should().BeOfType<MessageEnvelope<CompleteChatMessage>>();
        result.From.Should().Be(_ollamaClientAgent.Name);
    }

    [Fact]
    public async Task GenerateReplyAsync_ReturnsValidJsonMessageContent_WhenCalled()
    {
        var messages = new IMessage[] { new TextMessage(Role.User, "Hello") };
        IMessage result = await _ollamaClientAgent.GenerateReplyAsync(messages, new OllamaReplyOptions
        {
            Format = FormatType.Json
        });

        result.Should().NotBeNull();
        result.Should().BeOfType<MessageEnvelope<CompleteChatMessage>>();
        result.From.Should().Be(_ollamaClientAgent.Name);

        string jsonContent = ((MessageEnvelope<CompleteChatMessage>)result).Content.Message!.Value;
        bool isValidJson = IsValidJson(jsonContent);
        isValidJson.Should().BeTrue();
    }

    [Fact]
    public async Task GenerateStreamingReplyAsync_ReturnsValidMessages_WhenCalled()
    {
        var messages = new IMessage[] { new TextMessage(Role.User, "Hello") };
        IAsyncEnumerable<IStreamingMessage> streamingResults = await _ollamaClientAgent.GenerateStreamingReplyAsync(messages);

        IStreamingMessage? finalReply = default;
        await foreach (IStreamingMessage message in streamingResults)
        {
            message.Should().NotBeNull();
            message.From.Should().Be(_ollamaClientAgent.Name);
            finalReply = message;
        }

        finalReply.Should().BeOfType<MessageEnvelope<CompleteChatMessage>>();
    }

    public static bool IsValidJson(string input)
    {
        try
        {
            JsonDocument.Parse(input);
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
        catch (Exception ex)
        {
            Console.WriteLine("An unexpected exception occurred: " + ex.Message);
            return false;
        }
    }
}
