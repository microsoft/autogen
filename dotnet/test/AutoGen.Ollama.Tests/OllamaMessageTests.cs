// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaMessageTests.cs

using AutoGen.Core;
using AutoGen.Tests;
using FluentAssertions;
using Xunit;
namespace AutoGen.Ollama.Tests;

public class OllamaMessageTests
{
    [Fact]
    public async Task ItProcessUserTextMessageAsync()
    {
        var messageConnector = new OllamaMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Message>>();
                var message = (IMessage<Message>)innerMessage;
                message.Content.Value.Should().Be("Hello");
                message.Content.Images.Should().BeNullOrEmpty();
                message.Content.Role.Should().Be("user");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        // when from is null and role is user
        await agent.SendAsync("Hello");

        // when from is user and role is user
        var userMessage = new TextMessage(Role.User, "Hello", from: "user");
        await agent.SendAsync(userMessage);

        // when from is user but role is assistant
        userMessage = new TextMessage(Role.Assistant, "Hello", from: "user");
        await agent.SendAsync(userMessage);
    }

    [Fact]
    public async Task ItProcessStreamingTextMessageAsync()
    {
        var messageConnector = new OllamaMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterStreamingMiddleware(messageConnector);

        var messageChunks = Enumerable.Range(0, 10)
            .Select(i => new ChatResponseUpdate()
            {
                Message = new Message()
                {
                    Value = i.ToString(),
                    Role = "assistant",
                }
            })
            .Select(m => MessageEnvelope.Create(m));

        IMessage? finalReply = null;
        await foreach (var reply in agent.GenerateStreamingReplyAsync(messageChunks))
        {
            reply.Should().BeAssignableTo<IMessage>();
            finalReply = reply;
        }

        finalReply.Should().BeOfType<TextMessage>();
        var textMessage = (TextMessage)finalReply!;
        textMessage.GetContent().Should().Be("0123456789");
    }

    [Fact]
    public async Task ItProcessAssistantTextMessageAsync()
    {
        var messageConnector = new OllamaMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Message>>();
                var message = (IMessage<Message>)innerMessage;
                message.Content.Value.Should().Be("Hello");
                message.Content.Images.Should().BeNullOrEmpty();
                message.Content.Role.Should().Be("assistant");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        // when from is null and role is assistant
        var assistantMessage = new TextMessage(Role.Assistant, "Hello");
        await agent.SendAsync(assistantMessage);

        // when from is assistant and role is assistant
        assistantMessage = new TextMessage(Role.Assistant, "Hello", from: "assistant");
        await agent.SendAsync(assistantMessage);

        // when from is assistant but role is user
        assistantMessage = new TextMessage(Role.User, "Hello", from: "assistant");
        await agent.SendAsync(assistantMessage);
    }

    [Fact]
    public async Task ItProcessSystemTextMessageAsync()
    {
        var messageConnector = new OllamaMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Message>>();
                var message = (IMessage<Message>)innerMessage;
                message.Content.Value.Should().Be("Hello");
                message.Content.Images.Should().BeNullOrEmpty();
                message.Content.Role.Should().Be("system");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        // when role is system
        var systemMessage = new TextMessage(Role.System, "Hello");
        await agent.SendAsync(systemMessage);
    }

    [Fact]
    public async Task ItProcessImageMessageAsync()
    {
        var messageConnector = new OllamaMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Message>>();
                var message = (IMessage<Message>)innerMessage;
                message.Content.Images!.Count.Should().Be(1);
                message.Content.Role.Should().Be("user");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        var square = Path.Combine("images", "square.png");
        BinaryData imageBinaryData = BinaryData.FromBytes(File.ReadAllBytes(square), "image/png");
        var imageMessage = new ImageMessage(Role.User, imageBinaryData);
        await agent.SendAsync(imageMessage);
    }

    [Fact]
    public async Task ItProcessMultiModalMessageAsync()
    {
        var messageConnector = new OllamaMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var message = msgs.First();
                message.Should().BeOfType<MessageEnvelope<Message>>();

                var multiModalMessage = (IMessage<Message>)message;
                multiModalMessage.Content.Images!.Count.Should().Be(1);
                multiModalMessage.Content.Value.Should().Be("Hello");

                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        var square = Path.Combine("images", "square.png");
        BinaryData imageBinaryData = BinaryData.FromBytes(File.ReadAllBytes(square), "image/png");
        var imageMessage = new ImageMessage(Role.User, imageBinaryData);
        var textMessage = new TextMessage(Role.User, "Hello");
        var multiModalMessage = new MultiModalMessage(Role.User, [textMessage, imageMessage]);

        await agent.SendAsync(multiModalMessage);
    }
}
