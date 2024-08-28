// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralClientAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;
using AutoGen.Mistral.Extension;

namespace AutoGen.Mistral;

/// <summary>
/// Mistral client agent.
/// 
/// <para>This agent supports the following input message types:</para>
/// <list type="bullet">
/// <para><see cref="MessageEnvelope{T}"/> where T is <see cref="ChatMessage"/></para>
/// </list>
/// 
/// <para>This agent returns the following message types:</para>
/// <list type="bullet">
/// <para><see cref="MessageEnvelope{T}"/> where T is <see cref="ChatCompletionResponse"/></para>
/// </list>
/// 
/// You can register this agent with <see cref="MistralAgentExtension.RegisterMessageConnector(AutoGen.Mistral.MistralClientAgent, AutoGen.Mistral.MistralChatMessageConnector?)"/>
/// to support more AutoGen message types.
/// </summary>
public class MistralClientAgent : IStreamingAgent
{
    private readonly MistralClient _client;
    private readonly string _systemMessage;
    private readonly string _model;
    private readonly int? _randomSeed;
    private readonly bool _jsonOutput = false;
    private ToolChoiceEnum? _toolChoice;

    /// <summary>
    /// Create a new instance of <see cref="MistralClientAgent"/>.
    /// </summary>
    /// <param name="client"><see cref="MistralClient"/></param>
    /// <param name="name">the name of this agent</param>
    /// <param name="model">the mistral model id.</param>
    /// <param name="systemMessage">system message.</param>
    /// <param name="randomSeed">the seed to generate output.</param>
    /// <param name="toolChoice">tool choice strategy.</param>
    /// <param name="jsonOutput">use json output.</param>
    public MistralClientAgent(
        MistralClient client,
        string name,
        string model,
        string systemMessage = "You are a helpful AI assistant",
        int? randomSeed = null,
        ToolChoiceEnum? toolChoice = null,
        bool jsonOutput = false)
    {
        _client = client;
        Name = name;
        _systemMessage = systemMessage;
        _model = model;
        _randomSeed = randomSeed;
        _jsonOutput = jsonOutput;
        _toolChoice = toolChoice;
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var request = BuildChatRequest(messages, options);
        var response = await _client.CreateChatCompletionsAsync(request);

        return new MessageEnvelope<ChatCompletionResponse>(response, from: this.Name);
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var request = BuildChatRequest(messages, options);
        var response = _client.StreamingChatCompletionsAsync(request);

        await foreach (var content in response)
        {
            yield return new MessageEnvelope<ChatCompletionResponse>(content, from: this.Name);
        }
    }

    private ChatCompletionRequest BuildChatRequest(IEnumerable<IMessage> messages, GenerateReplyOptions? options)
    {
        var chatHistory = BuildChatHistory(messages);
        var chatRequest = new ChatCompletionRequest(model: _model, messages: chatHistory.ToList(), temperature: options?.Temperature, randomSeed: _randomSeed)
        {
            Stop = options?.StopSequence,
            MaxTokens = options?.MaxToken,
            ResponseFormat = _jsonOutput ? new ResponseFormat() { ResponseFormatType = "json_object" } : null,
        };

        if (options?.Functions != null)
        {
            chatRequest.Tools = options.Functions.Select(f => new FunctionTool(f.ToMistralFunctionDefinition())).ToList();
            chatRequest.ToolChoice = _toolChoice ?? ToolChoiceEnum.Auto;
        }

        return chatRequest;
    }

    private IEnumerable<ChatMessage> BuildChatHistory(IEnumerable<IMessage> messages)
    {
        var history = messages.Select(m => m switch
        {
            IMessage<ChatMessage> chatMessage => chatMessage.Content,
            _ => throw new ArgumentException("Invalid message type")
        });

        // if there's no system message in the history, add one to the beginning
        if (!history.Any(m => m.Role == ChatMessage.RoleEnum.System))
        {
            history = new[] { new ChatMessage(ChatMessage.RoleEnum.System, _systemMessage) }.Concat(history);
        }

        return history;
    }
}
