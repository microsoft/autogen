﻿// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaAgentTests.cs

using System.Text.Json;
using AutoGen.Core;
using AutoGen.Tests;
using FluentAssertions;

namespace AutoGen.Ollama.Tests;

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

        var message = new Message("user", "hey how are you");
        var messages = new IMessage[] { MessageEnvelope.Create(message, from: modelName) };
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

        var message = new Message("user", "What color is the sky at different times of the day? Respond using JSON");
        var messages = new IMessage[] { MessageEnvelope.Create(message, from: modelName) };
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

        var msg = new Message("user", "hey how are you");
        var messages = new IMessage[] { MessageEnvelope.Create(msg, from: modelName) };
        IStreamingMessage? finalReply = default;
        await foreach (IStreamingMessage message in ollamaAgent.GenerateStreamingReplyAsync(messages))
        {
            message.Should().NotBeNull();
            message.From.Should().Be(ollamaAgent.Name);
            var streamingMessage = (IMessage<ChatResponseUpdate>)message;
            if (streamingMessage.Content.Done)
            {
                finalReply = message;
                break;
            }
            else
            {
                streamingMessage.Content.Message.Should().NotBeNull();
                streamingMessage.Content.Done.Should().BeFalse();
            }
        }

        finalReply.Should().BeOfType<MessageEnvelope<ChatResponse>>();
        var update = ((MessageEnvelope<ChatResponse>)finalReply!).Content;
        update.Done.Should().BeTrue();
        update.TotalDuration.Should().BeGreaterThan(0);
    }

    [ApiKeyFact("OLLAMA_HOST")]
    public async Task ItReturnValidMessageUsingLLavaAsync()
    {
        var host = Environment.GetEnvironmentVariable("OLLAMA_HOST")
                   ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        var modelName = "llava:latest";
        var ollamaAgent = BuildOllamaAgent(host, modelName);
        var squareImagePath = Path.Combine("images", "square.png");
        var base64Image = Convert.ToBase64String(File.ReadAllBytes(squareImagePath));
        var message = new Message()
        {
            Role = "user",
            Value = "What's in this image?",
            Images = [base64Image],
        };

        var messages = new IMessage[] { MessageEnvelope.Create(message, from: modelName) };
        var reply = await ollamaAgent.GenerateReplyAsync(messages);

        reply.Should().BeOfType<MessageEnvelope<ChatResponse>>();
        var chatResponse = ((MessageEnvelope<ChatResponse>)reply).Content;
        chatResponse.Message.Should().NotBeNull();
    }

    [ApiKeyFact("OLLAMA_HOST")]
    public async Task ItReturnValidStreamingMessageUsingLLavaAsync()
    {
        var host = Environment.GetEnvironmentVariable("OLLAMA_HOST")
                   ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        var modelName = "llava:latest";
        var ollamaAgent = BuildOllamaAgent(host, modelName);
        var squareImagePath = Path.Combine("images", "square.png");
        var base64Image = Convert.ToBase64String(File.ReadAllBytes(squareImagePath));
        var imageMessage = new Message()
        {
            Role = "user",
            Value = "What's in this image?",
            Images = [base64Image],
        };

        var messages = new IMessage[] { MessageEnvelope.Create(imageMessage, from: modelName) };

        IStreamingMessage? finalReply = default;
        await foreach (IStreamingMessage message in ollamaAgent.GenerateStreamingReplyAsync(messages))
        {
            message.Should().NotBeNull();
            message.From.Should().Be(ollamaAgent.Name);
            var streamingMessage = (IMessage<ChatResponseUpdate>)message;
            if (streamingMessage.Content.Done)
            {
                finalReply = message;
                break;
            }
            else
            {
                streamingMessage.Content.Message.Should().NotBeNull();
                streamingMessage.Content.Done.Should().BeFalse();
            }
        }

        finalReply.Should().BeOfType<MessageEnvelope<ChatResponse>>();
        var update = ((MessageEnvelope<ChatResponse>)finalReply!).Content;
        update.Done.Should().BeTrue();
        update.TotalDuration.Should().BeGreaterThan(0);
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
