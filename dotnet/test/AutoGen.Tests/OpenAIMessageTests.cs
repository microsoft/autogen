// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIMessageTests.cs

using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using ApprovalTests;
using ApprovalTests.Namers;
using ApprovalTests.Reporters;
using AutoGen.OpenAI;
using Azure.AI.OpenAI;
using Xunit;

namespace AutoGen.Tests;

public class OpenAIMessageTests
{
    private readonly JsonSerializerOptions jsonSerializerOptions = new JsonSerializerOptions
    {
        WriteIndented = true,
        IgnoreReadOnlyProperties = false,
    };

    [Fact]
    [UseReporter(typeof(DiffReporter))]
    [UseApprovalSubdirectory("ApprovalTests")]
    public void BasicMessageTest()
    {
        IMessage[] messages = [
            new TextMessage(Role.System, "You are a helpful AI assistant"),
            new TextMessage(Role.User, "Hello", "user"),
            new TextMessage(Role.Assistant, "How can I help you?", from: "assistant"),
            new Message(Role.System, "You are a helpful AI assistant"),
            new Message(Role.User, "Hello", "user"),
            new Message(Role.Assistant, "How can I help you?", from: "assistant"),
            new Message(Role.Function, "result", "user"),
            new Message(Role.Assistant, null, "assistant")
            {
                FunctionName = "functionName",
                FunctionArguments = "functionArguments",
            },
            new ImageMessage(Role.User, "https://example.com/image.png", "user"),
            new MultiModalMessage(
                [
                    new TextMessage(Role.User, "Hello", "user"),
                    new ImageMessage(Role.User, "https://example.com/image.png", "user"),
                ], "user"),
            new ToolCallMessage("test", "test", "assistant"),
            new ToolCallResultMessage("result", new ToolCallMessage("test", "test", "assistant"), "user"),
            new ParallelToolCallResultMessage(
                [
                    new ToolCallResultMessage("result", new ToolCallMessage("test", "test", "assistant"), "user"),
                    new ToolCallResultMessage("result", new ToolCallMessage("test", "test", "assistant"), "user"),
                ], "user"),
            new AggregateMessage(
                [
                    new ToolCallMessage("test", "test", "assistant"),
                    new ToolCallMessage("test", "test", "assistant"),
                ], "assistant"),
        ];

        var agent = new EchoAgent("assistant");

        var oaiMessages = messages.Select(m => (m, agent.ToOpenAIChatRequestMessage(m).Select(m => m.Content)));
        VerifyOAIMessages(oaiMessages);
    }

    private void VerifyOAIMessages(IEnumerable<(IMessage, IEnumerable<ChatRequestMessage>)> messages)
    {
        var jsonObjects = messages.Select(pair =>
        {
            var (originalMessage, ms) = pair;
            var objs = new List<object>();
            foreach (var m in ms)
            {
                object? obj = null;
                if (m is ChatRequestUserMessage userMessage)
                {
                    obj = new
                    {
                        Role = userMessage.Role.ToString(),
                        Content = userMessage.Content,
                        MultiModaItem = userMessage.MultimodalContentItems?.Select(item =>
                        {
                            return item switch
                            {
                                ChatMessageImageContentItem imageContentItem => new
                                {
                                    Type = "Image",
                                    ImageUrl = imageContentItem.ImageUrl,
                                } as object,
                                ChatMessageTextContentItem textContentItem => new
                                {
                                    Type = "Text",
                                    Text = textContentItem.Text,
                                } as object,
                                _ => throw new System.NotImplementedException(),
                            };
                        }),
                    };
                }

                if (m is ChatRequestAssistantMessage assistantMessage)
                {
                    obj = new
                    {
                        Role = assistantMessage.Role.ToString(),
                        Content = assistantMessage.Content,
                        TooCall = assistantMessage.ToolCalls.Select(tc =>
                        {
                            return tc switch
                            {
                                ChatCompletionsFunctionToolCall functionToolCall => new
                                {
                                    Type = "Function",
                                    Name = functionToolCall.Name,
                                    Arguments = functionToolCall.Arguments,
                                    Id = functionToolCall.Id,
                                } as object,
                                _ => throw new System.NotImplementedException(),
                            };
                        }),
                        FunctionCallName = assistantMessage.FunctionCall?.Name,
                        FunctionCallArguments = assistantMessage.FunctionCall?.Arguments,
                    };
                }

                if (m is ChatRequestSystemMessage systemMessage)
                {
                    obj = new
                    {
                        Role = systemMessage.Role.ToString(),
                        Content = systemMessage.Content,
                    };
                }

                if (m is ChatRequestFunctionMessage functionMessage)
                {
                    obj = new
                    {
                        Role = functionMessage.Role.ToString(),
                        Content = functionMessage.Content,
                        Name = functionMessage.Name,
                    };
                }

                if (m is ChatRequestToolMessage toolCallMessage)
                {
                    obj = new
                    {
                        Role = toolCallMessage.Role.ToString(),
                        Content = toolCallMessage.Content,
                        ToolCallId = toolCallMessage.ToolCallId,
                    };
                }

                objs.Add(obj ?? throw new System.NotImplementedException());
            }

            return new
            {
                OriginalMessage = originalMessage.ToString(),
                ConvertedMessages = objs,
            };
        });

        var json = JsonSerializer.Serialize(jsonObjects, this.jsonSerializerOptions);
        Approvals.Verify(json);
    }
}
