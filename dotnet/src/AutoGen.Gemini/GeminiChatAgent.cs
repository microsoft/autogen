// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiChatAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;
using AutoGen.Gemini.Extension;
using Google.Cloud.AIPlatform.V1;
using Google.Protobuf.Collections;
namespace AutoGen.Gemini;

public class GeminiChatAgent : IStreamingAgent
{
    private readonly IGeminiClient client;
    private readonly string? systemMessage;
    private readonly string model;
    private readonly ToolConfig? toolConfig;
    private readonly RepeatedField<SafetySetting>? safetySettings;
    private readonly string responseMimeType;
    private readonly Tool[]? tools;

    /// <summary>
    /// Create <see cref="GeminiChatAgent"/> that connects to Gemini.
    /// </summary>
    /// <param name="client">the gemini client to use. e.g. <see cref="VertexGeminiClient"/> </param>
    /// <param name="name">agent name</param>
    /// <param name="model">the model id. It needs to be in the format of 
    /// 'projects/{project}/locations/{location}/publishers/{provider}/models/{model}' if the <paramref name="client"/> is <see cref="VertexGeminiClient"/></param>
    /// <param name="systemMessage">system message</param>
    /// <param name="toolConfig">tool config</param>
    /// <param name="tools">tools</param>
    /// <param name="safetySettings">safety settings</param>
    /// <param name="responseMimeType">response mime type, available values are ['application/json', 'text/plain'], default is 'text/plain'</param>
    public GeminiChatAgent(
        IGeminiClient client,
        string name,
        string model,
        string? systemMessage = null,
        ToolConfig? toolConfig = null,
        Tool[]? tools = null,
        RepeatedField<SafetySetting>? safetySettings = null,
        string responseMimeType = "text/plain")
    {
        this.client = client;
        this.Name = name;
        this.systemMessage = systemMessage;
        this.model = model;
        this.toolConfig = toolConfig;
        this.safetySettings = safetySettings;
        this.responseMimeType = responseMimeType;
        this.tools = tools;
    }

    /// <summary>
    /// Create <see cref="GeminiChatAgent"/> that connects to Vertex AI.
    /// </summary>
    /// <param name="name">agent name</param>
    /// <param name="systemMessage">system message</param>
    /// <param name="model">the name of gemini model, e.g. gemini-1.5-flash-001</param>
    /// <param name="project">project id</param>
    /// <param name="location">model location</param>
    /// <param name="provider">model provider, default is 'google'</param>
    /// <param name="toolConfig">tool config</param>
    /// <param name="tools">tools</param>
    /// <param name="safetySettings"></param>
    /// <param name="responseMimeType">response mime type, available values are ['application/json', 'text/plain'], default is 'text/plain'</param>
    public GeminiChatAgent(
        string name,
        string model,
        string project,
        string location,
        string provider = "google",
        string? systemMessage = null,
        ToolConfig? toolConfig = null,
        Tool[]? tools = null,
        RepeatedField<SafetySetting>? safetySettings = null,
        string responseMimeType = "text/plain")
        : this(
              client: new VertexGeminiClient(location),
              name: name,
              model: $"projects/{project}/locations/{location}/publishers/{provider}/models/{model}",
              systemMessage: systemMessage,
              toolConfig: toolConfig,
              tools: tools,
              safetySettings: safetySettings,
              responseMimeType: responseMimeType)
    {
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        var request = BuildChatRequest(messages, options);
        var response = await this.client.GenerateContentAsync(request, cancellationToken: cancellationToken).ConfigureAwait(false);

        return MessageEnvelope.Create(response, this.Name);
    }

    public async IAsyncEnumerable<IStreamingMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var request = BuildChatRequest(messages, options);
        var response = this.client.GenerateContentStreamAsync(request);

        await foreach (var item in response.WithCancellation(cancellationToken).ConfigureAwait(false))
        {
            yield return MessageEnvelope.Create(item, this.Name);
        }
    }

    private GenerateContentRequest BuildChatRequest(IEnumerable<IMessage> messages, GenerateReplyOptions? options)
    {
        var geminiMessages = messages.Select(m => m switch
        {
            IMessage<Content> contentMessage => contentMessage.Content,
            _ => throw new NotSupportedException($"Message type {m.GetType()} is not supported.")
        });

        var systemMessage = this.systemMessage switch
        {
            null => null,
            string message => new Content
            {
                Parts = { new[] { new Part { Text = message } } },
                Role = "system"
            }
        };

        var request = new GenerateContentRequest()
        {
            Contents = { geminiMessages },
            SystemInstruction = systemMessage,
            Model = this.model,
            GenerationConfig = new GenerationConfig
            {
                StopSequences = { options?.StopSequence ?? Enumerable.Empty<string>() },
                ResponseMimeType = this.responseMimeType,
                CandidateCount = 1,
            },
            Tools = { this.tools ?? Enumerable.Empty<Tool>() }
        };

        if (this.toolConfig is not null)
        {
            request.ToolConfig = this.toolConfig;
        }

        if (this.safetySettings is not null)
        {
            request.SafetySettings.Add(this.safetySettings);
        }

        if (options?.MaxToken.HasValue is true)
        {
            request.GenerationConfig.MaxOutputTokens = options.MaxToken.Value;
        }

        if (options?.Temperature.HasValue is true)
        {
            request.GenerationConfig.Temperature = options.Temperature.Value;
        }

        if (options?.Functions is { Length: > 0 })
        {
            foreach (var function in options.Functions)
            {
                request.Tools.Add(function.ToTool());
            }
        }

        return request;
    }
}
