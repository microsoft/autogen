// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIMessageTests.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Threading.Tasks;
using ApprovalTests;
using ApprovalTests.Namers;
using ApprovalTests.Reporters;
using AutoGen.Tests;
using Azure.AI.OpenAI;
using FluentAssertions;
using Xunit;

namespace AutoGen.OpenAI.V1.Tests;

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
    public async Task ItProcessUserTextMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestUserMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().Be("Hello");
                chatRequestMessage.Name.Should().Be("user");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        IMessage message = new TextMessage(Role.User, "Hello", "user");
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItShortcutChatRequestMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestUserMessage>>();

                var chatRequestMessage = (ChatRequestUserMessage)((MessageEnvelope<ChatRequestUserMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().Be("hello");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        var userMessage = new ChatRequestUserMessage("hello");
        var chatRequestMessage = MessageEnvelope.Create(userMessage);
        await agent.GenerateReplyAsync([chatRequestMessage]);
    }

    [Fact]
    public async Task ItShortcutMessageWhenStrictModelIsFalseAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<string>>();

                var chatRequestMessage = ((MessageEnvelope<string>)innerMessage!).Content;
                chatRequestMessage.Should().Be("hello");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        var userMessage = "hello";
        var chatRequestMessage = MessageEnvelope.Create(userMessage);
        await agent.GenerateReplyAsync([chatRequestMessage]);
    }

    [Fact]
    public async Task ItThrowExceptionWhenStrictModeIsTrueAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector(true);
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(middleware);

        // user message
        var userMessage = "hello";
        var chatRequestMessage = MessageEnvelope.Create(userMessage);
        Func<Task> action = async () => await agent.GenerateReplyAsync([chatRequestMessage]);

        await action.Should().ThrowAsync<InvalidOperationException>().WithMessage("Invalid message type: MessageEnvelope`1");
    }

    [Fact]
    public async Task ItProcessAssistantTextMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestAssistantMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().Be("How can I help you?");
                chatRequestMessage.Name.Should().Be("assistant");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // assistant message
        IMessage message = new TextMessage(Role.Assistant, "How can I help you?", "assistant");
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItProcessSystemTextMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestSystemMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().Be("You are a helpful AI assistant");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // system message
        IMessage message = new TextMessage(Role.System, "You are a helpful AI assistant");
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItProcessImageMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestUserMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().BeNullOrEmpty();
                chatRequestMessage.Name.Should().Be("user");
                chatRequestMessage.MultimodalContentItems.Count().Should().Be(1);
                chatRequestMessage.MultimodalContentItems.First().Should().BeOfType<ChatMessageImageContentItem>();
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        IMessage message = new ImageMessage(Role.User, "https://example.com/image.png", "user");
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItThrowExceptionWhenProcessingImageMessageFromSelfAndStrictModeIsTrueAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector(true);
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(middleware);

        var imageMessage = new ImageMessage(Role.Assistant, "https://example.com/image.png", "assistant");
        Func<Task> action = async () => await agent.GenerateReplyAsync([imageMessage]);

        await action.Should().ThrowAsync<InvalidOperationException>().WithMessage("Invalid message type: ImageMessage");
    }

    [Fact]
    public async Task ItProcessMultiModalMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestUserMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().BeNullOrEmpty();
                chatRequestMessage.Name.Should().Be("user");
                chatRequestMessage.MultimodalContentItems.Count().Should().Be(2);
                chatRequestMessage.MultimodalContentItems.First().Should().BeOfType<ChatMessageTextContentItem>();
                chatRequestMessage.MultimodalContentItems.Last().Should().BeOfType<ChatMessageImageContentItem>();
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        IMessage message = new MultiModalMessage(
            Role.User,
            [
                new TextMessage(Role.User, "Hello", "user"),
                new ImageMessage(Role.User, "https://example.com/image.png", "user"),
            ], "user");
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItThrowExceptionWhenProcessingMultiModalMessageFromSelfAndStrictModeIsTrueAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector(true);
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(middleware);

        var multiModalMessage = new MultiModalMessage(
            Role.Assistant,
            [
                new TextMessage(Role.User, "Hello", "assistant"),
                new ImageMessage(Role.User, "https://example.com/image.png", "assistant"),
            ], "assistant");

        Func<Task> action = async () => await agent.GenerateReplyAsync([multiModalMessage]);

        await action.Should().ThrowAsync<InvalidOperationException>().WithMessage("Invalid message type: MultiModalMessage");
    }

    [Fact]
    public async Task ItProcessToolCallMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestAssistantMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                // when the message is a tool call message
                // the name field should not be set
                // please visit OpenAIChatRequestMessageConnector class for more information
                chatRequestMessage.Name.Should().BeNullOrEmpty();
                chatRequestMessage.ToolCalls.Count().Should().Be(1);
                chatRequestMessage.Content.Should().Be("textContent");
                chatRequestMessage.ToolCalls.First().Should().BeOfType<ChatCompletionsFunctionToolCall>();
                var functionToolCall = (ChatCompletionsFunctionToolCall)chatRequestMessage.ToolCalls.First();
                functionToolCall.Name.Should().Be("test");
                functionToolCall.Id.Should().Be("test");
                functionToolCall.Arguments.Should().Be("test");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        IMessage message = new ToolCallMessage("test", "test", "assistant")
        {
            Content = "textContent",
        };
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItProcessParallelToolCallMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestAssistantMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().BeNullOrEmpty();

                // when the message is a tool call message
                // the name field should not be set
                // please visit OpenAIChatRequestMessageConnector class for more information
                chatRequestMessage.Name.Should().BeNullOrEmpty();
                chatRequestMessage.ToolCalls.Count().Should().Be(2);
                for (int i = 0; i < chatRequestMessage.ToolCalls.Count(); i++)
                {
                    chatRequestMessage.ToolCalls.ElementAt(i).Should().BeOfType<ChatCompletionsFunctionToolCall>();
                    var functionToolCall = (ChatCompletionsFunctionToolCall)chatRequestMessage.ToolCalls.ElementAt(i);
                    functionToolCall.Name.Should().Be("test");
                    functionToolCall.Id.Should().Be($"test_{i}");
                    functionToolCall.Arguments.Should().Be("test");
                }
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        var toolCalls = new[]
        {
            new ToolCall("test", "test"),
            new ToolCall("test", "test"),
        };
        IMessage message = new ToolCallMessage(toolCalls, "assistant");
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItThrowExceptionWhenProcessingToolCallMessageFromUserAndStrictModeIsTrueAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector(strictMode: true);
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(middleware);

        var toolCallMessage = new ToolCallMessage("test", "test", "user");
        Func<Task> action = async () => await agent.GenerateReplyAsync([toolCallMessage]);
        await action.Should().ThrowAsync<InvalidOperationException>().WithMessage("Invalid message type: ToolCallMessage");
    }

    [Fact]
    public async Task ItProcessToolCallResultMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestToolMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().Be("result");
                chatRequestMessage.ToolCallId.Should().Be("test");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        IMessage message = new ToolCallResultMessage("result", "test", "test", "user");
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItProcessParallelToolCallResultMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                msgs.Count().Should().Be(2);

                for (int i = 0; i < msgs.Count(); i++)
                {
                    var innerMessage = msgs.ElementAt(i);
                    innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                    var chatRequestMessage = (ChatRequestToolMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                    chatRequestMessage.Content.Should().Be("result");
                    chatRequestMessage.ToolCallId.Should().Be($"test_{i}");
                }
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        var toolCalls = new[]
        {
            new ToolCall("test", "test", "result"),
            new ToolCall("test", "test", "result"),
        };
        IMessage message = new ToolCallResultMessage(toolCalls, "user");
        await agent.GenerateReplyAsync([message]);
    }

    [Fact]
    public async Task ItProcessFunctionCallMiddlewareMessageFromUserAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestUserMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().Be("result");
                chatRequestMessage.Name.Should().Be("user");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        var toolCallMessage = new ToolCallMessage("test", "test", "user");
        var toolCallResultMessage = new ToolCallResultMessage("result", "test", "test", "user");
        var aggregateMessage = new AggregateMessage<ToolCallMessage, ToolCallResultMessage>(toolCallMessage, toolCallResultMessage, "user");
        await agent.GenerateReplyAsync([aggregateMessage]);
    }

    [Fact]
    public async Task ItProcessFunctionCallMiddlewareMessageFromAssistantAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                msgs.Count().Should().Be(2);
                var innerMessage = msgs.Last();
                innerMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var chatRequestMessage = (ChatRequestToolMessage)((MessageEnvelope<ChatRequestMessage>)innerMessage!).Content;
                chatRequestMessage.Content.Should().Be("result");
                chatRequestMessage.ToolCallId.Should().Be("test");

                var toolCallMessage = msgs.First();
                toolCallMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var toolCallRequestMessage = (ChatRequestAssistantMessage)((MessageEnvelope<ChatRequestMessage>)toolCallMessage!).Content;
                toolCallRequestMessage.Content.Should().BeNullOrEmpty();
                toolCallRequestMessage.ToolCalls.Count().Should().Be(1);
                toolCallRequestMessage.ToolCalls.First().Should().BeOfType<ChatCompletionsFunctionToolCall>();
                var functionToolCall = (ChatCompletionsFunctionToolCall)toolCallRequestMessage.ToolCalls.First();
                functionToolCall.Name.Should().Be("test");
                functionToolCall.Id.Should().Be("test");
                functionToolCall.Arguments.Should().Be("test");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        var toolCallMessage = new ToolCallMessage("test", "test", "assistant");
        var toolCallResultMessage = new ToolCallResultMessage("result", "test", "test", "assistant");
        var aggregateMessage = new ToolCallAggregateMessage(toolCallMessage, toolCallResultMessage, "assistant");
        await agent.GenerateReplyAsync([aggregateMessage]);
    }

    [Fact]
    public async Task ItProcessParallelFunctionCallMiddlewareMessageFromAssistantAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, _) =>
            {
                msgs.Count().Should().Be(3);
                var toolCallMessage = msgs.First();
                toolCallMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                var toolCallRequestMessage = (ChatRequestAssistantMessage)((MessageEnvelope<ChatRequestMessage>)toolCallMessage!).Content;
                toolCallRequestMessage.Content.Should().BeNullOrEmpty();
                toolCallRequestMessage.ToolCalls.Count().Should().Be(2);

                for (int i = 0; i < toolCallRequestMessage.ToolCalls.Count(); i++)
                {
                    toolCallRequestMessage.ToolCalls.ElementAt(i).Should().BeOfType<ChatCompletionsFunctionToolCall>();
                    var functionToolCall = (ChatCompletionsFunctionToolCall)toolCallRequestMessage.ToolCalls.ElementAt(i);
                    functionToolCall.Name.Should().Be("test");
                    functionToolCall.Id.Should().Be($"test_{i}");
                    functionToolCall.Arguments.Should().Be("test");
                }

                for (int i = 1; i < msgs.Count(); i++)
                {
                    var toolCallResultMessage = msgs.ElementAt(i);
                    toolCallResultMessage!.Should().BeOfType<MessageEnvelope<ChatRequestMessage>>();
                    var toolCallResultRequestMessage = (ChatRequestToolMessage)((MessageEnvelope<ChatRequestMessage>)toolCallResultMessage!).Content;
                    toolCallResultRequestMessage.Content.Should().Be("result");
                    toolCallResultRequestMessage.ToolCallId.Should().Be($"test_{i - 1}");
                }

                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(middleware);

        // user message
        var toolCalls = new[]
        {
            new ToolCall("test", "test", "result"),
            new ToolCall("test", "test", "result"),
        };
        var toolCallMessage = new ToolCallMessage(toolCalls, "assistant");
        var toolCallResultMessage = new ToolCallResultMessage(toolCalls, "assistant");
        var aggregateMessage = new AggregateMessage<ToolCallMessage, ToolCallResultMessage>(toolCallMessage, toolCallResultMessage, "assistant");
        await agent.GenerateReplyAsync([aggregateMessage]);
    }

    [Fact]
    public async Task ItConvertChatResponseMessageToTextMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(middleware);

        // text message
        var textMessage = CreateInstance<ChatResponseMessage>(ChatRole.Assistant, "hello");
        var chatRequestMessage = MessageEnvelope.Create(textMessage);

        var message = await agent.GenerateReplyAsync([chatRequestMessage]);
        message.Should().BeOfType<TextMessage>();
        message.GetContent().Should().Be("hello");
        message.GetRole().Should().Be(Role.Assistant);
    }

    [Fact]
    public async Task ItConvertChatResponseMessageToToolCallMessageAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(middleware);

        // tool call message
        var toolCallMessage = CreateInstance<ChatResponseMessage>(ChatRole.Assistant, "textContent", new[] { new ChatCompletionsFunctionToolCall("test", "test", "test") }, new FunctionCall("test", "test"), CreateInstance<AzureChatExtensionsMessageContext>(), new Dictionary<string, BinaryData>());
        var chatRequestMessage = MessageEnvelope.Create(toolCallMessage);
        var message = await agent.GenerateReplyAsync([chatRequestMessage]);
        message.Should().BeOfType<ToolCallMessage>();
        message.GetToolCalls()!.Count().Should().Be(1);
        message.GetToolCalls()!.First().FunctionName.Should().Be("test");
        message.GetToolCalls()!.First().FunctionArguments.Should().Be("test");
        message.GetContent().Should().Be("textContent");
    }

    [Fact]
    public async Task ItReturnOriginalMessageWhenStrictModeIsFalseAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(middleware);

        // text message
        var textMessage = "hello";
        var messageToSend = MessageEnvelope.Create(textMessage);

        var message = await agent.GenerateReplyAsync([messageToSend]);
        message.Should().BeOfType<MessageEnvelope<string>>();
    }

    [Fact]
    public async Task ItThrowInvalidOperationExceptionWhenStrictModeIsTrueAsync()
    {
        var middleware = new OpenAIChatRequestMessageConnector(true);
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(middleware);

        // text message
        var textMessage = new ChatRequestUserMessage("hello");
        var messageToSend = MessageEnvelope.Create(textMessage);
        Func<Task> action = async () => await agent.GenerateReplyAsync([messageToSend]);

        await action.Should().ThrowAsync<InvalidOperationException>().WithMessage("Invalid return message type MessageEnvelope`1");
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
            //oaiMessages.First().Should().BeOfType<IMessage<ChatRequestMessage>>();
            if (oaiMessages.First() is IMessage<ChatRequestMessage> chatRequestMessage)
            {
                chatRequestMessage.Content.Should().Be(oaiMessage);
            }
            else
            {
                // fail the test
                Assert.True(false);
            }
        }
    }
    private void VerifyOAIMessages(IEnumerable<(IMessage, IEnumerable<IMessage>)> messages)
    {
        var jsonObjects = messages.Select(pair =>
        {
            var (originalMessage, ms) = pair;
            var objs = new List<object>();
            foreach (var m in ms)
            {
                object? obj = null;
                var chatRequestMessage = (m as IMessage<ChatRequestMessage>)?.Content;
                if (chatRequestMessage is ChatRequestUserMessage userMessage)
                {
                    obj = new
                    {
                        Role = userMessage.Role.ToString(),
                        Content = userMessage.Content,
                        Name = userMessage.Name,
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

                if (chatRequestMessage is ChatRequestAssistantMessage assistantMessage)
                {
                    obj = new
                    {
                        Role = assistantMessage.Role.ToString(),
                        Content = assistantMessage.Content,
                        Name = assistantMessage.Name,
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

                if (chatRequestMessage is ChatRequestSystemMessage systemMessage)
                {
                    obj = new
                    {
                        Name = systemMessage.Name,
                        Role = systemMessage.Role.ToString(),
                        Content = systemMessage.Content,
                    };
                }

                if (chatRequestMessage is ChatRequestFunctionMessage functionMessage)
                {
                    obj = new
                    {
                        Role = functionMessage.Role.ToString(),
                        Content = functionMessage.Content,
                        Name = functionMessage.Name,
                    };
                }

                if (chatRequestMessage is ChatRequestToolMessage toolCallMessage)
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

    private static T CreateInstance<T>(params object[] args)
    {
        var type = typeof(T);
        var instance = type.Assembly.CreateInstance(
            type.FullName!, false,
            BindingFlags.Instance | BindingFlags.NonPublic,
            null, args, null, null);
        return (T)instance!;
    }
}
