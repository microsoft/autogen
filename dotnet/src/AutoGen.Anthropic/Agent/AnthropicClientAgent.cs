using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Anthropic.DTO;
using AutoGen.Core;

namespace AutoGen.Anthropic;

public class AnthropicClientAgent : IStreamingAgent
{
    private readonly AnthropicClient _anthropicClient;
    public string Name { get; }
    private readonly string _modelName;
    private readonly string _systemMessage;
    private readonly decimal _temperature;
    private readonly int _maxTokens;

    public AnthropicClientAgent(
        AnthropicClient anthropicClient,
        string name,
        string modelName,
        string systemMessage = "You are a helpful AI assistant",
        decimal temperature = 0.7m,
        int maxTokens = 1024)
    {
        Name = name;
        _anthropicClient = anthropicClient;
        _modelName = modelName;
        _systemMessage = systemMessage;
        _temperature = temperature;
        _maxTokens = maxTokens;
    }

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var response = await _anthropicClient.CreateChatCompletionsAsync(CreateParameters(messages, options, false), cancellationToken);
        return new MessageEnvelope<ChatCompletionResponse>(response, from: this.Name);
    }

    public async IAsyncEnumerable<IStreamingMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        await foreach (var message in _anthropicClient.StreamingChatCompletionsAsync(
                           CreateParameters(messages, options, true), cancellationToken))
        {
            yield return new MessageEnvelope<ChatCompletionResponse>(message, from: this.Name);
        }
    }

    private ChatCompletionRequest CreateParameters(IEnumerable<IMessage> messages, GenerateReplyOptions? options, bool shouldStream)
    {
        var chatCompletionRequest = new ChatCompletionRequest()
        {
            SystemMessage = _systemMessage,
            MaxTokens = options?.MaxToken ?? _maxTokens,
            Model = _modelName,
            Stream = shouldStream,
            Temperature = (decimal?)options?.Temperature ?? _temperature,
        };

        chatCompletionRequest.Messages = BuildMessages(messages);

        return chatCompletionRequest;
    }

    private List<ChatMessage> BuildMessages(IEnumerable<IMessage> messages)
    {
        List<ChatMessage> chatMessages = new();
        foreach (IMessage? message in messages)
        {
            switch (message)
            {
                case IMessage<ChatMessage> chatMessage when chatMessage.Content.Role == "system":
                    throw new InvalidOperationException(
                        "system message has already been set and only one system message is supported. \"system\" role for input messages in the Message");

                case IMessage<ChatMessage> chatMessage:
                    chatMessages.Add(chatMessage.Content);
                    break;

                default:
                    throw new ArgumentException($"Unexpected message type: {message?.GetType()}");
            }
        }

        return chatMessages;
    }
}
