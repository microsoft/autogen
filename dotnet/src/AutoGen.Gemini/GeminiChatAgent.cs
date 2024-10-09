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
    /// Create <see cref="GeminiChatAgent"/> that connects to Gemini using <see cref="GoogleGeminiClient"/>
    /// </summary>
    /// <param name="name">agent name</param>
    /// <param name="model">the name of gemini model, e.g. gemini-1.5-flash-001</param>
    /// <param name="apiKey">google gemini api key</param>
    /// <param name="systemMessage">system message</param>
    /// <param name="toolConfig">tool config</param>
    /// <param name="tools">tools</param>
    /// <param name="safetySettings"></param>
    /// <param name="responseMimeType">response mime type, available values are ['application/json', 'text/plain'], default is 'text/plain'</param>
    /// /// <example>
    /// <![CDATA[
    /// [!code-csharp[Chat_With_Google_Gemini](~/../samples/AutoGen.Gemini.Sample/Chat_With_Google_Gemini.cs?name=Create_Gemini_Agent)]
    /// ]]>
    /// </example>
    public GeminiChatAgent(
        string name,
        string model,
        string apiKey,
        string systemMessage = "You are a helpful AI assistant",
        ToolConfig? toolConfig = null,
        Tool[]? tools = null,
        RepeatedField<SafetySetting>? safetySettings = null,
        string responseMimeType = "text/plain")
        : this(
              client: new GoogleGeminiClient(apiKey),
              name: name,
              model: model,
              systemMessage: systemMessage,
              toolConfig: toolConfig,
              tools: tools,
              safetySettings: safetySettings,
              responseMimeType: responseMimeType)
    {
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
    /// <example>
    /// <![CDATA[
    /// [!code-csharp[Chat_With_Vertex_Gemini](~/../samples/AutoGen.Gemini.Sample/Chat_With_Vertex_Gemini.cs?name=Create_Gemini_Agent)]
    /// ]]>
    /// </example>
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

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, [EnumeratorCancellation] CancellationToken cancellationToken = default)
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

        // there are several rules applies to the messages that can be sent to Gemini in a multi-turn chat
        // - The first message must be from the user or function
        // - The (user|model) roles must alternate e.g. (user, model, user, model, ...)
        // - The last message must be from the user or function

        // check if the first message is from the user
        if (geminiMessages.FirstOrDefault()?.Role != "user" && geminiMessages.FirstOrDefault()?.Role != "function")
        {
            throw new ArgumentException("The first message must be from the user or function", nameof(messages));
        }

        // check if the last message is from the user
        if (geminiMessages.LastOrDefault()?.Role != "user" && geminiMessages.LastOrDefault()?.Role != "function")
        {
            throw new ArgumentException("The last message must be from the user or function", nameof(messages));
        }

        // merge continuous messages with the same role into one message
        var mergedMessages = geminiMessages.Aggregate(new List<Content>(), (acc, message) =>
        {
            if (acc.Count == 0 || acc.Last().Role != message.Role)
            {
                acc.Add(message);
            }
            else
            {
                acc.Last().Parts.AddRange(message.Parts);
            }

            return acc;
        });

        var systemMessage = this.systemMessage switch
        {
            null => null,
            string message => new Content
            {
                Parts = { new[] { new Part { Text = message } } },
                Role = "system_instruction"
            }
        };

        List<Tool> tools = this.tools?.ToList() ?? new List<Tool>();

        var request = new GenerateContentRequest()
        {
            Contents = { mergedMessages },
            SystemInstruction = systemMessage,
            Model = this.model,
            GenerationConfig = new GenerationConfig
            {
                StopSequences = { options?.StopSequence ?? Enumerable.Empty<string>() },
                ResponseMimeType = this.responseMimeType,
                CandidateCount = 1,
            },
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
                tools.Add(new Tool
                {
                    FunctionDeclarations = { function.ToFunctionDeclaration() },
                });
            }
        }

        // merge tools into one tool
        // because multipe tools are currently not supported by Gemini
        // see https://github.com/googleapis/python-aiplatform/issues/3771
        var aggregatedTool = new Tool
        {
            FunctionDeclarations = { tools.SelectMany(t => t.FunctionDeclarations) },
        };

        if (aggregatedTool is { FunctionDeclarations: { Count: > 0 } })
        {
            request.Tools.Add(aggregatedTool);
        }

        return request;
    }
}
