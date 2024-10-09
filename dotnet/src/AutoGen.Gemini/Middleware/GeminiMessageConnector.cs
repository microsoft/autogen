// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;
using Google.Cloud.AIPlatform.V1;
using Google.Protobuf;
using Google.Protobuf.WellKnownTypes;
using static Google.Cloud.AIPlatform.V1.Candidate.Types;
using IMessage = AutoGen.Core.IMessage;

namespace AutoGen.Gemini;

public class GeminiMessageConnector : IStreamingMiddleware
{
    /// <summary>
    /// if true, the connector will throw an exception if it encounters an unsupport message type.
    /// Otherwise, it will ignore processing the message and return the message as is.
    /// </summary>
    private readonly bool strictMode;

    /// <summary>
    /// Initializes a new instance of the <see cref="GeminiMessageConnector"/> class.
    /// </summary>
    /// <param name="strictMode">whether to throw an exception if it encounters an unsupport message type.
    /// If true, the connector will throw an exception if it encounters an unsupport message type.
    /// If false, it will ignore processing the message and return the message as is.</param>
    public GeminiMessageConnector(bool strictMode = false)
    {
        this.strictMode = strictMode;
    }

    public string Name => nameof(GeminiMessageConnector);

    public async IAsyncEnumerable<IMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var messages = ProcessMessage(context.Messages, agent);

        var bucket = new List<GenerateContentResponse>();

        await foreach (var reply in agent.GenerateStreamingReplyAsync(messages, context.Options, cancellationToken))
        {
            if (reply is Core.IMessage<GenerateContentResponse> m)
            {
                // if m.Content is empty and stop reason is Stop, ignore the message
                if (m.Content.Candidates.Count == 1 && m.Content.Candidates[0].Content.Parts.Count == 1 && m.Content.Candidates[0].Content.Parts[0].DataCase == Part.DataOneofCase.Text)
                {
                    var text = m.Content.Candidates[0].Content.Parts[0].Text;
                    var stopReason = m.Content.Candidates[0].FinishReason;
                    if (string.IsNullOrEmpty(text) && stopReason == FinishReason.Stop)
                    {
                        continue;
                    }
                }

                bucket.Add(m.Content);

                yield return PostProcessStreamingMessage(m.Content, agent);
            }
            else if (strictMode)
            {
                throw new InvalidOperationException($"Unsupported message type: {reply.GetType()}");
            }
            else
            {
                yield return reply;
            }

            // aggregate the message updates from bucket into a single message
            if (bucket is { Count: > 0 })
            {
                var isTextMessageUpdates = bucket.All(m => m.Candidates.Count == 1 && m.Candidates[0].Content.Parts.Count == 1 && m.Candidates[0].Content.Parts[0].DataCase == Part.DataOneofCase.Text);
                var isFunctionCallUpdates = bucket.Any(m => m.Candidates.Count == 1 && m.Candidates[0].Content.Parts.Count == 1 && m.Candidates[0].Content.Parts[0].DataCase == Part.DataOneofCase.FunctionCall);
                if (isTextMessageUpdates)
                {
                    var text = string.Join(string.Empty, bucket.Select(m => m.Candidates[0].Content.Parts[0].Text));
                    var textMessage = new TextMessage(Role.Assistant, text, agent.Name);

                    yield return textMessage;
                }
                else if (isFunctionCallUpdates)
                {
                    var functionCallParts = bucket.Where(m => m.Candidates.Count == 1 && m.Candidates[0].Content.Parts.Count == 1 && m.Candidates[0].Content.Parts[0].DataCase == Part.DataOneofCase.FunctionCall)
                        .Select(m => m.Candidates[0].Content.Parts[0]).ToList();

                    var toolCalls = new List<ToolCall>();
                    foreach (var part in functionCallParts)
                    {
                        var fc = part.FunctionCall;
                        var toolCall = new ToolCall(fc.Name, fc.Args.ToString());

                        toolCalls.Add(toolCall);
                    }

                    var toolCallMessage = new ToolCallMessage(toolCalls, agent.Name);

                    yield return toolCallMessage;
                }
                else
                {
                    throw new InvalidOperationException("The response should contain either text or tool calls.");
                }
            }
        }
    }

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        var messages = ProcessMessage(context.Messages, agent);
        var reply = await agent.GenerateReplyAsync(messages, context.Options, cancellationToken);

        return reply switch
        {
            Core.IMessage<GenerateContentResponse> m => PostProcessMessage(m.Content, agent),
            _ when strictMode => throw new InvalidOperationException($"Unsupported message type: {reply.GetType()}"),
            _ => reply,
        };
    }

    private IMessage PostProcessStreamingMessage(GenerateContentResponse m, IAgent agent)
    {
        this.ValidateGenerateContentResponse(m);

        var candidate = m.Candidates[0];
        var parts = candidate.Content.Parts;

        if (parts.Count == 1 && parts[0].DataCase == Part.DataOneofCase.Text)
        {
            var content = parts[0].Text;
            return new TextMessageUpdate(Role.Assistant, content, agent.Name);
        }
        else
        {
            var toolCalls = new List<ToolCall>();
            foreach (var part in parts)
            {
                if (part.DataCase == Part.DataOneofCase.FunctionCall)
                {
                    var fc = part.FunctionCall;
                    var toolCall = new ToolCall(fc.Name, fc.Args.ToString());

                    toolCalls.Add(toolCall);
                }
            }

            if (toolCalls.Count > 0)
            {
                var toolCallMessage = new ToolCallMessage(toolCalls, agent.Name);
                return toolCallMessage;
            }
            else
            {
                throw new InvalidOperationException("The response should contain either text or tool calls.");
            }
        }
    }

    private IMessage PostProcessMessage(GenerateContentResponse m, IAgent agent)
    {
        this.ValidateGenerateContentResponse(m);
        var candidate = m.Candidates[0];
        var parts = candidate.Content.Parts;

        if (parts.Count == 1 && parts[0].DataCase == Part.DataOneofCase.Text)
        {
            var content = parts[0].Text;
            return new TextMessage(Role.Assistant, content, agent.Name);
        }
        else
        {
            var toolCalls = new List<ToolCall>();
            foreach (var part in parts)
            {
                if (part.DataCase == Part.DataOneofCase.FunctionCall)
                {
                    var fc = part.FunctionCall;
                    var toolCall = new ToolCall(fc.Name, fc.Args.ToString());

                    toolCalls.Add(toolCall);
                }
            }

            if (toolCalls.Count > 0)
            {
                var toolCallMessage = new ToolCallMessage(toolCalls, agent.Name);
                return toolCallMessage;
            }
            else
            {
                throw new InvalidOperationException("The response should contain either text or tool calls.");
            }
        }
    }

    private IEnumerable<IMessage> ProcessMessage(IEnumerable<IMessage> messages, IAgent agent)
    {
        return messages.SelectMany(m =>
        {
            if (m is Core.IMessage<Content> messageEnvelope)
            {
                return [m];
            }
            else
            {
                return m switch
                {
                    TextMessage textMessage => ProcessTextMessage(textMessage, agent),
                    ImageMessage imageMessage => ProcessImageMessage(imageMessage, agent),
                    MultiModalMessage multiModalMessage => ProcessMultiModalMessage(multiModalMessage, agent),
                    ToolCallMessage toolCallMessage => ProcessToolCallMessage(toolCallMessage, agent),
                    ToolCallResultMessage toolCallResultMessage => ProcessToolCallResultMessage(toolCallResultMessage, agent),
                    ToolCallAggregateMessage toolCallAggregateMessage => ProcessToolCallAggregateMessage(toolCallAggregateMessage, agent),
                    _ when strictMode => throw new InvalidOperationException($"Unsupported message type: {m.GetType()}"),
                    _ => [m],
                };
            }
        });
    }

    private IEnumerable<IMessage> ProcessToolCallAggregateMessage(ToolCallAggregateMessage toolCallAggregateMessage, IAgent agent)
    {
        var parseAsUser = ShouldParseAsUser(toolCallAggregateMessage, agent);
        if (parseAsUser)
        {
            var content = toolCallAggregateMessage.GetContent();

            if (content is string str)
            {
                var textMessage = new TextMessage(Role.User, str, toolCallAggregateMessage.From);

                return ProcessTextMessage(textMessage, agent);
            }

            return [];
        }
        else
        {
            var toolCallContents = ProcessToolCallMessage(toolCallAggregateMessage.Message1, agent);
            var toolCallResultContents = ProcessToolCallResultMessage(toolCallAggregateMessage.Message2, agent);

            return toolCallContents.Concat(toolCallResultContents);
        }
    }

    private void ValidateGenerateContentResponse(GenerateContentResponse response)
    {
        if (response.Candidates.Count != 1)
        {
            throw new InvalidOperationException("The response should contain exactly one candidate.");
        }

        var candidate = response.Candidates[0];
        if (candidate.Content is null)
        {
            var finishReason = candidate.FinishReason;
            var finishMessage = candidate.FinishMessage;

            throw new InvalidOperationException($"The response should contain content but the content is empty. FinishReason: {finishReason}, FinishMessage: {finishMessage}");
        }
    }

    private IEnumerable<IMessage> ProcessToolCallResultMessage(ToolCallResultMessage toolCallResultMessage, IAgent _)
    {
        var functionCallResultParts = new List<Part>();
        foreach (var toolCallResult in toolCallResultMessage.ToolCalls)
        {
            if (toolCallResult.Result is null)
            {
                continue;
            }

            // if result is already a json object, use it as is
            var json = toolCallResult.Result;
            try
            {
                JsonNode.Parse(json);
            }
            catch (JsonException)
            {
                // if the result is not a json object, wrap it in a json object
                var result = new { result = json };
                json = JsonSerializer.Serialize(result);
            }
            var part = new Part
            {
                FunctionResponse = new FunctionResponse
                {
                    Name = toolCallResult.FunctionName,
                    Response = Struct.Parser.ParseJson(json),
                }
            };

            functionCallResultParts.Add(part);
        }

        var content = new Content
        {
            Parts = { functionCallResultParts },
            Role = "function",
        };

        return [MessageEnvelope.Create(content, toolCallResultMessage.From)];
    }

    private IEnumerable<IMessage> ProcessToolCallMessage(ToolCallMessage toolCallMessage, IAgent agent)
    {
        var shouldParseAsUser = ShouldParseAsUser(toolCallMessage, agent);
        if (strictMode && shouldParseAsUser)
        {
            throw new InvalidOperationException("ToolCallMessage is not supported as user role in Gemini.");
        }

        var functionCallParts = new List<Part>();
        foreach (var toolCall in toolCallMessage.ToolCalls)
        {
            var part = new Part
            {
                FunctionCall = new FunctionCall
                {
                    Name = toolCall.FunctionName,
                    Args = Struct.Parser.ParseJson(toolCall.FunctionArguments),
                }
            };

            functionCallParts.Add(part);
        }
        var content = new Content
        {
            Parts = { functionCallParts },
            Role = "model"
        };

        return [MessageEnvelope.Create(content, toolCallMessage.From)];
    }

    private IEnumerable<IMessage> ProcessMultiModalMessage(MultiModalMessage multiModalMessage, IAgent agent)
    {
        var parts = new List<Part>();
        foreach (var message in multiModalMessage.Content)
        {
            if (message is TextMessage textMessage)
            {
                parts.Add(new Part { Text = textMessage.Content });
            }
            else if (message is ImageMessage imageMessage)
            {
                parts.Add(CreateImagePart(imageMessage));
            }
            else
            {
                throw new InvalidOperationException($"Unsupported message type: {message.GetType()}");
            }
        }

        var shouldParseAsUser = ShouldParseAsUser(multiModalMessage, agent);

        if (strictMode && !shouldParseAsUser)
        {
            // image message is not supported as model role in Gemini
            throw new InvalidOperationException("Image message is not supported as model role in Gemini.");
        }

        var content = new Content
        {
            Parts = { parts },
            Role = shouldParseAsUser ? "user" : "model",
        };

        return [MessageEnvelope.Create(content, multiModalMessage.From)];
    }

    private IEnumerable<IMessage> ProcessTextMessage(TextMessage textMessage, IAgent agent)
    {
        if (textMessage.Role == Role.System)
        {
            // there are only user | model role in Gemini
            // if the role is system and the strict mode is enabled, throw an exception
            if (strictMode)
            {
                throw new InvalidOperationException("System role is not supported in Gemini.");
            }

            // if strict mode is not enabled, parse the message as a user message
            var content = new Content
            {
                Parts = { new[] { new Part { Text = textMessage.Content } } },
                Role = "user",
            };

            return [MessageEnvelope.Create(content, textMessage.From)];
        }

        var shouldParseAsUser = ShouldParseAsUser(textMessage, agent);

        if (shouldParseAsUser)
        {
            var content = new Content
            {
                Parts = { new[] { new Part { Text = textMessage.Content } } },
                Role = "user",
            };

            return [MessageEnvelope.Create(content, textMessage.From)];
        }
        else
        {
            var content = new Content
            {
                Parts = { new[] { new Part { Text = textMessage.Content } } },
                Role = "model",
            };

            return [MessageEnvelope.Create(content, textMessage.From)];
        }
    }

    private IEnumerable<IMessage> ProcessImageMessage(ImageMessage imageMessage, IAgent agent)
    {
        var imagePart = CreateImagePart(imageMessage);
        var shouldParseAsUser = ShouldParseAsUser(imageMessage, agent);

        if (strictMode && !shouldParseAsUser)
        {
            // image message is not supported as model role in Gemini
            throw new InvalidOperationException("Image message is not supported as model role in Gemini.");
        }

        var content = new Content
        {
            Parts = { imagePart },
            Role = shouldParseAsUser ? "user" : "model",
        };

        return [MessageEnvelope.Create(content, imageMessage.From)];
    }

    private Part CreateImagePart(ImageMessage message)
    {
        if (message.Url is string url)
        {
            return new Part
            {
                FileData = new FileData
                {
                    FileUri = url,
                    MimeType = message.MimeType
                }
            };
        }
        else if (message.Data is BinaryData data)
        {
            return new Part
            {
                InlineData = new Blob
                {
                    MimeType = message.MimeType,
                    Data = ByteString.CopyFrom(data.ToArray()),
                }
            };
        }
        else
        {
            throw new InvalidOperationException("Invalid ImageMessage, the data or url must be provided");
        }
    }

    private bool ShouldParseAsUser(IMessage message, IAgent agent)
    {
        return message switch
        {
            TextMessage textMessage => (textMessage.Role == Role.User && textMessage.From is null)
                || (textMessage.From != agent.Name),
            _ => message.From != agent.Name,
        };
    }
}
