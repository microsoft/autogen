// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiMessageTests.cs

using AutoGen.Core;
using AutoGen.Gemini.Middleware;
using AutoGen.Tests;
using FluentAssertions;
using Google.Cloud.AIPlatform.V1;
using Xunit;

namespace AutoGen.Gemini.Tests;

public class GeminiMessageTests
{
    [Fact]
    public async Task ItProcessUserTextMessageAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Content>>();
                var message = (IMessage<Content>)innerMessage;
                message.Content.Parts.Count.Should().Be(1);
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
    public async Task ItProcessAssistantTextMessageAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Content>>();
                var message = (IMessage<Content>)innerMessage;
                message.Content.Parts.Count.Should().Be(1);
                message.Content.Role.Should().Be("model");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        // when from is user and role is assistant
        var message = new TextMessage(Role.User, "Hello", from: agent.Name);
        await agent.SendAsync(message);

        // when from is assistant and role is assistant
        message = new TextMessage(Role.Assistant, "Hello", from: agent.Name);
        await agent.SendAsync(message);
    }

    [Fact]
    public async Task ItProcessSystemTextMessageAsUserMessageWhenStrictModeIsFalseAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Content>>();
                var message = (IMessage<Content>)innerMessage;
                message.Content.Parts.Count.Should().Be(1);
                message.Content.Role.Should().Be("user");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        var message = new TextMessage(Role.System, "Hello", from: agent.Name);
        await agent.SendAsync(message);
    }

    [Fact]
    public async Task ItThrowExceptionOnSystemMessageWhenStrictModeIsTrueAsync()
    {
        var messageConnector = new GeminiMessageConnector(true);
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(messageConnector);

        var message = new TextMessage(Role.System, "Hello", from: agent.Name);
        var action = new Func<Task>(async () => await agent.SendAsync(message));
        await action.Should().ThrowAsync<InvalidOperationException>();
    }

    [Fact]
    public async Task ItProcessUserImageMessageAsInlineDataAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Content>>();
                var message = (IMessage<Content>)innerMessage;
                message.Content.Parts.Count.Should().Be(1);
                message.Content.Role.Should().Be("user");
                message.Content.Parts.First().DataCase.Should().Be(Part.DataOneofCase.InlineData);
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        var imagePath = Path.Combine("testData", "images", "image.png");
        var image = File.ReadAllBytes(imagePath);
        var message = new ImageMessage(Role.User, BinaryData.FromBytes(image, "image/png"));
        message.MimeType.Should().Be("image/png");

        await agent.SendAsync(message);
    }

    [Fact]
    public async Task ItProcessUserImageMessageAsFileDataAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Content>>();
                var message = (IMessage<Content>)innerMessage;
                message.Content.Parts.Count.Should().Be(1);
                message.Content.Role.Should().Be("user");
                message.Content.Parts.First().DataCase.Should().Be(Part.DataOneofCase.FileData);
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        var imagePath = Path.Combine("testData", "images", "image.png");
        var url = new Uri(Path.GetFullPath(imagePath)).AbsoluteUri;
        var message = new ImageMessage(Role.User, url);
        message.MimeType.Should().Be("image/png");

        await agent.SendAsync(message);
    }

    [Fact]
    public async Task ItProcessMultiModalMessageAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Content>>();
                var message = (IMessage<Content>)innerMessage;
                message.Content.Parts.Count.Should().Be(2);
                message.Content.Role.Should().Be("user");
                message.Content.Parts.First().DataCase.Should().Be(Part.DataOneofCase.Text);
                message.Content.Parts.Last().DataCase.Should().Be(Part.DataOneofCase.FileData);
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        var imagePath = Path.Combine("testData", "images", "image.png");
        var url = new Uri(Path.GetFullPath(imagePath)).AbsoluteUri;
        var message = new ImageMessage(Role.User, url);
        message.MimeType.Should().Be("image/png");
        var textMessage = new TextMessage(Role.User, "What's in this image?");
        var multiModalMessage = new MultiModalMessage(Role.User, [textMessage, message]);

        await agent.SendAsync(multiModalMessage);
    }

    [Fact]
    public async Task ItProcessToolCallMessageAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Content>>();
                var message = (IMessage<Content>)innerMessage;
                message.Content.Role.Should().BeEmpty();
                message.Content.Parts.First().DataCase.Should().Be(Part.DataOneofCase.FunctionCall);
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        var toolCallMessage = new ToolCallMessage("test", "{}", "user");
        await agent.SendAsync(toolCallMessage);
    }

    [Fact]
    public async Task ItProcessToolCallResultMessageAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                msgs.Count().Should().Be(1);
                var innerMessage = msgs.First();
                innerMessage.Should().BeOfType<MessageEnvelope<Content>>();
                var message = (IMessage<Content>)innerMessage;
                message.Content.Role.Should().BeEmpty();
                message.Content.Parts.First().DataCase.Should().Be(Part.DataOneofCase.FunctionResponse);
                message.Content.Parts.First().FunctionResponse.Response.ToString().Should().Be("{ \"result\": \"result\" }");
                return await innerAgent.GenerateReplyAsync(msgs);
            })
            .RegisterMiddleware(messageConnector);

        var message = new ToolCallResultMessage("result", "test", "{}", "user");
        await agent.SendAsync(message);

        // when the result is already a json object string
        message = new ToolCallResultMessage("{ \"result\": \"result\" }", "test", "{}", "user");
        await agent.SendAsync(message);
    }

    [Fact]
    public async Task ItProcessToolCallAggregateMessageAsync()
    {
        throw new NotImplementedException();
    }

    [Fact]
    public async Task ItThrowExceptionWhenProcessingUnknownMessageTypeInStrictModeAsync()
    {
        throw new NotImplementedException();
    }

    [Fact]
    public async Task ItReturnUnknownMessageTypeInNonStrictModeAsync()
    {
        throw new NotImplementedException();
    }

    [Fact]
    public async Task ItShortcircuitContentTypeAsync()
    {
        var messageConnector = new GeminiMessageConnector();
        var agent = new EchoAgent("assistant")
            .RegisterMiddleware(async (msgs, _, innerAgent, ct) =>
            {
                var message = msgs.First();
                message.Should().BeOfType<MessageEnvelope<Content>>();

                return message;
            })
            .RegisterMiddleware(messageConnector);

        var message = new Content()
        {
            Parts = { new Part { Text = "Hello" } },
            Role = "user",
        };

        await agent.SendAsync(MessageEnvelope.Create(message, from: agent.Name));
    }
}
