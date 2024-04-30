// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaAgentTests.cs

using System.Text.Json;
using AutoGen.Core;
using AutoGen.Tests;
using FluentAssertions;

namespace Autogen.Ollama.Tests;

public class OllamaAgentTests
{

    [ApiKeyFact("OLLAMA_HOST", "OLLAMA_MODEL_NAME")]
    public async Task GenerateReplyAsync_ReturnsValidMessage_WhenCalled()
    {
        string host = Environment.GetEnvironmentVariable("OLLAMA_HOST")
                      ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        string modelName = Environment.GetEnvironmentVariable("OLLAMA_MODEL_NAME")
                           ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        OllamaAgent ollamaClientAgent = BuildOllamaAgent(host, modelName);

        var messages = new IMessage[] { new TextMessage(Role.User, "Hello") };
        IMessage result = await ollamaClientAgent.GenerateReplyAsync(messages);

        result.Should().NotBeNull();
        result.Should().BeOfType<MessageEnvelope<CompletedChatResponse>>();
        result.From.Should().Be(ollamaClientAgent.Name);
    }

    [ApiKeyFact("OLLAMA_HOST", "OLLAMA_MODEL_NAME")]
    public async Task GenerateReplyAsync_ReturnsValidJsonMessageContent_WhenCalled()
    {
        string host = Environment.GetEnvironmentVariable("OLLAMA_HOST")
                      ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        string modelName = Environment.GetEnvironmentVariable("OLLAMA_MODEL_NAME")
                           ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        OllamaAgent ollamaClientAgent = BuildOllamaAgent(host, modelName);

        var messages = new IMessage[] { new TextMessage(Role.User, "Hello") };
        IMessage result = await ollamaClientAgent.GenerateReplyAsync(messages, new OllamaReplyOptions
        {
            Format = FormatType.Json
        });

        result.Should().NotBeNull();
        result.Should().BeOfType<MessageEnvelope<CompletedChatResponse>>();
        result.From.Should().Be(ollamaClientAgent.Name);

        string jsonContent = ((MessageEnvelope<CompletedChatResponse>)result).Content.Message!.Value;
        bool isValidJson = IsValidJson(jsonContent);
        isValidJson.Should().BeTrue();
    }

    [ApiKeyFact("OLLAMA_HOST", "OLLAMA_MODEL_NAME")]
    public async Task GenerateStreamingReplyAsync_ReturnsValidMessages_WhenCalled()
    {
        string host = Environment.GetEnvironmentVariable("OLLAMA_HOST")
                      ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        string modelName = Environment.GetEnvironmentVariable("OLLAMA_MODEL_NAME")
                           ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        OllamaAgent ollamaClientAgent = BuildOllamaAgent(host, modelName);

        var messages = new IMessage[] { new TextMessage(Role.User, "Hello") };
        IAsyncEnumerable<IStreamingMessage> streamingResults = await ollamaClientAgent.GenerateStreamingReplyAsync(messages);

        IStreamingMessage? finalReply = default;
        await foreach (IStreamingMessage message in streamingResults)
        {
            message.Should().NotBeNull();
            message.From.Should().Be(ollamaClientAgent.Name);
            finalReply = message;
        }

        finalReply.Should().BeOfType<MessageEnvelope<CompletedChatResponse>>();
    }

    private static bool IsValidJson(string input)
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

    private static OllamaAgent BuildOllamaAgent(string host, string modelName)
    {
        var httpClient = new HttpClient
        {
            BaseAddress = new Uri(host),
            Timeout = TimeSpan.FromSeconds(250)
        };
        return new OllamaAgent(httpClient, "TestAgent", modelName);
    }
}
