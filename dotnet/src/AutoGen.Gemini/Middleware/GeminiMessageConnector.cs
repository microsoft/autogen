// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;
using Google.Cloud.AIPlatform.V1;
using Google.Protobuf;
using Google.Protobuf.WellKnownTypes;
using IMessage = AutoGen.Core.IMessage;

namespace AutoGen.Gemini.Middleware;

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

    public IAsyncEnumerable<IStreamingMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent, CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException();
    }

    public Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException();
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

    private IEnumerable<IMessage> ProcessToolCallResultMessage(ToolCallResultMessage toolCallResultMessage, IAgent agent)
    {
        var functionCallResultParts = new List<Part>();
        foreach (var toolCallResult in toolCallResultMessage.ToolCalls)
        {
            var part = new Part
            {
                FunctionResponse = new FunctionResponse
                {
                    Name = toolCallResult.FunctionName,
                    Response = Struct.Parser.ParseJson(toolCallResult.Result),
                }
            };

            functionCallResultParts.Add(part);
        }

        var content = new Content
        {
            Parts = { functionCallResultParts },
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
                Role = "system",
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
            _ => false,
        };
    }
}
