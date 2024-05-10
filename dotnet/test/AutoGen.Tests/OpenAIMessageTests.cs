// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIMessageTests.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using ApprovalTests;
using ApprovalTests.Namers;
using ApprovalTests.Reporters;
using AutoGen.OpenAI;
using Azure.AI.OpenAI;
using FluentAssertions;
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
            new MultiModalMessage(Role.Assistant,
                [
                    new TextMessage(Role.User, "Hello", "user"),
                    new ImageMessage(Role.User, "https://example.com/image.png", "user"),
                ], "user"),
            new ToolCallMessage("test", "test", "assistant"),
            new ToolCallResultMessage("result", "test", "test", "user"),
            new ToolCallResultMessage(
                [
                    new ToolCall("result", "test", "test"),
                    new ToolCall("result", "test", "test"),
                ], "user"),
            new ToolCallMessage(
                [
                    new ToolCall("test", "test"),
                    new ToolCall("test", "test"),
                ], "assistant"),
            new AggregateMessage<ToolCallMessage, ToolCallResultMessage>(
                message1: new ToolCallMessage("test", "test", "assistant"),
                message2: new ToolCallResultMessage("result", "test", "test", "assistant"), "assistant"),
        ];
        var openaiMessageConnectorMiddleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant");

        var oaiMessages = messages.Select(m => (m, openaiMessageConnectorMiddleware.ProcessIncomingMessages(agent, [m])));
        VerifyOAIMessages(oaiMessages);
    }

    [Fact]
    public void ToOpenAIChatRequestMessageTest()
    {
        var agent = new EchoAgent("assistant");
        var middleware = new OpenAIChatRequestMessageConnector();

        // user message
        IMessage message = new TextMessage(Role.User, "Hello", "user");
        var oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestUserMessage>();
        var userMessage = (ChatRequestUserMessage)oaiMessages.First();
        userMessage.Content.Should().Be("Hello");

        // user message test 2
        // even if Role is assistant, it should be converted to user message because it is from the user
        message = new TextMessage(Role.Assistant, "Hello", "user");
        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestUserMessage>();
        userMessage = (ChatRequestUserMessage)oaiMessages.First();
        userMessage.Content.Should().Be("Hello");

        // user message with multimodal content
        // image
        message = new ImageMessage(Role.User, "https://example.com/image.png", "user");
        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestUserMessage>();
        userMessage = (ChatRequestUserMessage)oaiMessages.First();
        userMessage.Content.Should().BeNullOrEmpty();
        userMessage.MultimodalContentItems.Count().Should().Be(1);
        userMessage.MultimodalContentItems.First().Should().BeOfType<ChatMessageImageContentItem>();

        // text and image
        message = new MultiModalMessage(
            Role.User,
            [
                new TextMessage(Role.User, "Hello", "user"),
                new ImageMessage(Role.User, "https://example.com/image.png", "user"),
            ], "user");
        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestUserMessage>();
        userMessage = (ChatRequestUserMessage)oaiMessages.First();
        userMessage.Content.Should().BeNullOrEmpty();
        userMessage.MultimodalContentItems.Count().Should().Be(2);
        userMessage.MultimodalContentItems.First().Should().BeOfType<ChatMessageTextContentItem>();

        // assistant text message
        message = new TextMessage(Role.Assistant, "How can I help you?", "assistant");
        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestAssistantMessage>();
        var assistantMessage = (ChatRequestAssistantMessage)oaiMessages.First();
        assistantMessage.Content.Should().Be("How can I help you?");

        // assistant text message with single tool call
        message = new ToolCallMessage("test", "test", "assistant");
        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestAssistantMessage>();
        assistantMessage = (ChatRequestAssistantMessage)oaiMessages.First();
        assistantMessage.Content.Should().BeNullOrEmpty();
        assistantMessage.ToolCalls.Count().Should().Be(1);
        assistantMessage.ToolCalls.First().Should().BeOfType<ChatCompletionsFunctionToolCall>();

        // user should not suppose to send tool call message
        message = new ToolCallMessage("test", "test", "user");
        Func<ChatRequestMessage> action = () => middleware.ProcessIncomingMessages(agent, [message]).First();
        action.Should().Throw<ArgumentException>().WithMessage("ToolCallMessage is not supported when message.From is not the same with agent");

        // assistant text message with multiple tool calls
        message = new ToolCallMessage(
            toolCalls:
            [
                new ToolCall("test", "test"),
                new ToolCall("test", "test"),
            ], "assistant");

        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestAssistantMessage>();
        assistantMessage = (ChatRequestAssistantMessage)oaiMessages.First();
        assistantMessage.Content.Should().BeNullOrEmpty();
        assistantMessage.ToolCalls.Count().Should().Be(2);

        // tool call result message
        message = new ToolCallResultMessage("result", "test", "test", "user");
        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestToolMessage>();
        var toolCallMessage = (ChatRequestToolMessage)oaiMessages.First();
        toolCallMessage.Content.Should().Be("result");

        // tool call result message with multiple tool calls
        message = new ToolCallResultMessage(
            toolCalls:
            [
                new ToolCall("result", "test", "test"),
                new ToolCall("result", "test", "test"),
            ], "user");

        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(2);
        oaiMessages.First().Should().BeOfType<ChatRequestToolMessage>();
        toolCallMessage = (ChatRequestToolMessage)oaiMessages.First();
        toolCallMessage.Content.Should().Be("test");
        oaiMessages.Last().Should().BeOfType<ChatRequestToolMessage>();
        toolCallMessage = (ChatRequestToolMessage)oaiMessages.Last();
        toolCallMessage.Content.Should().Be("test");

        // aggregate message test
        // aggregate message with tool call and tool call result will be returned by GPT agent if the tool call is automatically invoked inside agent
        message = new AggregateMessage<ToolCallMessage, ToolCallResultMessage>(
            message1: new ToolCallMessage("test", "test", "assistant"),
            message2: new ToolCallResultMessage("result", "test", "test", "assistant"), "assistant");

        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(2);
        oaiMessages.First().Should().BeOfType<ChatRequestAssistantMessage>();
        assistantMessage = (ChatRequestAssistantMessage)oaiMessages.First();
        assistantMessage.Content.Should().BeNullOrEmpty();
        assistantMessage.ToolCalls.Count().Should().Be(1);

        oaiMessages.Last().Should().BeOfType<ChatRequestToolMessage>();
        toolCallMessage = (ChatRequestToolMessage)oaiMessages.Last();
        toolCallMessage.Content.Should().Be("result");

        // aggregate message test 2
        // if the aggregate message is from user, it should be converted to user message
        message = new AggregateMessage<ToolCallMessage, ToolCallResultMessage>(
            message1: new ToolCallMessage("test", "test", "user"),
            message2: new ToolCallResultMessage("result", "test", "test", "user"), "user");

        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);

        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestUserMessage>();
        userMessage = (ChatRequestUserMessage)oaiMessages.First();
        userMessage.Content.Should().Be("result");

        // aggregate message test 3
        // if the aggregate message is from user and contains multiple tool call results, it should be converted to user message
        message = new AggregateMessage<ToolCallMessage, ToolCallResultMessage>(
            message1: new ToolCallMessage(
                toolCalls:
                [
                    new ToolCall("test", "test"),
                    new ToolCall("test", "test"),
                ], from: "user"),
            message2: new ToolCallResultMessage(
                toolCalls:
                [
                    new ToolCall("result", "test", "test"),
                    new ToolCall("result", "test", "test"),
                ], from: "user"), "user");

        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);
        oaiMessages.Count().Should().Be(2);
        oaiMessages.First().Should().BeOfType<ChatRequestUserMessage>();
        oaiMessages.Last().Should().BeOfType<ChatRequestUserMessage>();

        // system message
        message = new TextMessage(Role.System, "You are a helpful AI assistant");
        oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);
        oaiMessages.Count().Should().Be(1);
        oaiMessages.First().Should().BeOfType<ChatRequestSystemMessage>();
    }

    [Fact]
    public void ToOpenAIChatRequestMessageShortCircuitTest()
    {
        var agent = new EchoAgent("assistant");
        var middleware = new OpenAIChatRequestMessageConnector();
        ChatRequestMessage[] messages =
            [
                new ChatRequestUserMessage("Hello"),
                new ChatRequestAssistantMessage("How can I help you?"),
                new ChatRequestSystemMessage("You are a helpful AI assistant"),
                new ChatRequestFunctionMessage("result", "functionName"),
                new ChatRequestToolMessage("test", "test"),
            ];

        foreach (var oaiMessage in messages)
        {
            IMessage message = new MessageEnvelope<ChatRequestMessage>(oaiMessage);
            var oaiMessages = middleware.ProcessIncomingMessages(agent, [message]);
            oaiMessages.Count().Should().Be(1);
            oaiMessages.First().Should().Be(oaiMessage);
        }
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
                                    ImageUrl = GetImageUrlFromContent(imageContentItem),
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

    private object? GetImageUrlFromContent(ChatMessageImageContentItem content)
    {
        return content.GetType().GetProperty("ImageUrl", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)?.GetValue(content);
    }
}
