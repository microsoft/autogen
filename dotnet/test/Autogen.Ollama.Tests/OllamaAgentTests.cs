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
                           ?? throw new InvalidOperationException("OLLAMA_MODEL_NAME is not set.");
        OllamaAgent ollamaAgent = BuildOllamaAgent(host, modelName);

        var messages = new IMessage[] { new TextMessage(Role.User, "Hello, how are you") };
        IMessage result = await ollamaAgent.GenerateReplyAsync(messages);

        result.Should().NotBeNull();
        result.Should().BeOfType<MessageEnvelope<ChatResponse>>();
        result.From.Should().Be(ollamaAgent.Name);
    }

    [ApiKeyFact("OLLAMA_HOST", "OLLAMA_MODEL_NAME")]
    public async Task GenerateReplyAsync_ReturnsValidJsonMessageContent_WhenCalled()
    {
        string host = Environment.GetEnvironmentVariable("OLLAMA_HOST")
                      ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        string modelName = Environment.GetEnvironmentVariable("OLLAMA_MODEL_NAME")
                           ?? throw new InvalidOperationException("OLLAMA_MODEL_NAME is not set.");
        OllamaAgent ollamaAgent = BuildOllamaAgent(host, modelName);

        var messages = new IMessage[] { new TextMessage(Role.User, "Hello, how are you") };
        IMessage result = await ollamaAgent.GenerateReplyAsync(messages, new OllamaReplyOptions
        {
            Format = FormatType.Json
        });

        result.Should().NotBeNull();
        result.Should().BeOfType<MessageEnvelope<ChatResponse>>();
        result.From.Should().Be(ollamaAgent.Name);

        string jsonContent = ((MessageEnvelope<ChatResponse>)result).Content.Message!.Value;
        bool isValidJson = IsValidJsonMessage(jsonContent);
        isValidJson.Should().BeTrue();
    }

    [ApiKeyFact("OLLAMA_HOST", "OLLAMA_MODEL_NAME")]
    public async Task GenerateStreamingReplyAsync_ReturnsValidMessages_WhenCalled()
    {
        string host = Environment.GetEnvironmentVariable("OLLAMA_HOST")
                      ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        string modelName = Environment.GetEnvironmentVariable("OLLAMA_MODEL_NAME")
                           ?? throw new InvalidOperationException("OLLAMA_MODEL_NAME is not set.");
        OllamaAgent ollamaAgent = BuildOllamaAgent(host, modelName);

        var messages = new IMessage[] { new TextMessage(Role.User, "Hello how are you") };
        IStreamingMessage? finalReply = default;
        await foreach (IStreamingMessage message in ollamaAgent.GenerateStreamingReplyAsync(messages))
        {
            message.Should().NotBeNull();
            message.From.Should().Be(ollamaAgent.Name);
            finalReply = message;
        }

        finalReply.Should().BeOfType<MessageEnvelope<ChatResponse>>();
    }

    private static bool IsValidJsonMessage(string input)
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
            BaseAddress = new Uri(host)
        };
        return new OllamaAgent(httpClient, "TestAgent", modelName);
    }
}
