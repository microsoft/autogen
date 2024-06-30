// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicClientAgentTest.cs

using AutoGen.Anthropic.DTO;
using AutoGen.Anthropic.Extensions;
using AutoGen.Anthropic.Utils;
using AutoGen.Core;
using AutoGen.Tests;
using FluentAssertions;

namespace AutoGen.Anthropic.Tests;

public class AnthropicClientAgentTest
{
    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicAgentChatCompletionTestAsync()
    {
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var agent = new AnthropicClientAgent(
            client,
            name: "AnthropicAgent",
            AnthropicConstants.Claude3Haiku,
            systemMessage: "You are a helpful AI assistant that convert user message to upper case")
            .RegisterMessageConnector();

        var uppCaseMessage = new TextMessage(Role.User, "abcdefg");

        var reply = await agent.SendAsync(chatHistory: new[] { uppCaseMessage });

        reply.GetContent().Should().Contain("ABCDEFG");
        reply.From.Should().Be(agent.Name);
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicAgentTestProcessImageAsync()
    {
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);
        var agent = new AnthropicClientAgent(
            client,
            name: "AnthropicAgent",
            AnthropicConstants.Claude3Haiku).RegisterMessageConnector();

        var base64Image = await AnthropicTestUtils.Base64FromImageAsync("square.png");
        var imageMessage = new ChatMessage("user",
            [new ImageContent { Source = new ImageSource { MediaType = "image/png", Data = base64Image } }]);

        var messages = new IMessage[] { MessageEnvelope.Create(imageMessage) };

        // test streaming
        foreach (var message in messages)
        {
            var reply = agent.GenerateStreamingReplyAsync([message]);

            await foreach (var streamingMessage in reply)
            {
                streamingMessage.Should().BeOfType<TextMessageUpdate>();
                streamingMessage.As<TextMessageUpdate>().From.Should().Be(agent.Name);
            }
        }
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicAgentTestMultiModalAsync()
    {
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);
        var agent = new AnthropicClientAgent(
            client,
            name: "AnthropicAgent",
            AnthropicConstants.Claude3Haiku)
            .RegisterMessageConnector();

        var image = Path.Combine("images", "square.png");
        var binaryData = BinaryData.FromBytes(await File.ReadAllBytesAsync(image), "image/png");
        var imageMessage = new ImageMessage(Role.User, binaryData);
        var textMessage = new TextMessage(Role.User, "What's in this image?");
        var multiModalMessage = new MultiModalMessage(Role.User, [textMessage, imageMessage]);

        var reply = await agent.SendAsync(multiModalMessage);
        reply.Should().BeOfType<TextMessage>();
        reply.GetRole().Should().Be(Role.Assistant);
        reply.GetContent().Should().NotBeNullOrEmpty();
        reply.From.Should().Be(agent.Name);
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicAgentTestImageMessageAsync()
    {
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);
        var agent = new AnthropicClientAgent(
                client,
                name: "AnthropicAgent",
                AnthropicConstants.Claude3Haiku,
                systemMessage: "You are a helpful AI assistant that is capable of determining what an image is. Tell me a brief description of the image."
                )
            .RegisterMessageConnector();

        var image = Path.Combine("images", "square.png");
        var binaryData = BinaryData.FromBytes(await File.ReadAllBytesAsync(image), "image/png");
        var imageMessage = new ImageMessage(Role.User, binaryData);

        var reply = await agent.SendAsync(imageMessage);
        reply.Should().BeOfType<TextMessage>();
        reply.GetRole().Should().Be(Role.Assistant);
        reply.GetContent().Should().NotBeNullOrEmpty();
        reply.From.Should().Be(agent.Name);
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicAgentTestToolAsync()
    {
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var function = new TypeSafeFunctionCall();
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: new[] { function.WeatherReportFunctionContract },
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { function.WeatherReportFunctionContract.Name ?? string.Empty, function.WeatherReportWrapper },
            });

        var agent = new AnthropicClientAgent(
                client,
                name: "AnthropicAgent",
                AnthropicConstants.Claude3Haiku,
                systemMessage: "You are an LLM that is specialized in finding the weather !",
                tools: [AnthropicTestUtils.WeatherTool]
            )
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionCallMiddleware);

        var reply = await agent.SendAsync("What is the weather in Philadelphia?");
        reply.GetContent().Should().Be("Weather report for Philadelphia on today is sunny");
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicAgentFunctionCallMessageTest()
    {
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);
        var agent = new AnthropicClientAgent(
                client,
                name: "AnthropicAgent",
                AnthropicConstants.Claude3Haiku,
                systemMessage: "You are a helpful AI assistant.",
                tools: [AnthropicTestUtils.WeatherTool]
            )
            .RegisterMessageConnector();

        var weatherFunctionArgumets = """
                                      {
                                          "city": "Philadelphia",
                                          "date": "6/14/2024"
                                      }
                                      """;

        var function = new AnthropicTestFunctionCalls();
        var functionCallResult = await function.GetWeatherReportWrapper(weatherFunctionArgumets);
        var toolCall = new ToolCall(function.WeatherReportFunctionContract.Name!, weatherFunctionArgumets)
        {
            ToolCallId = "get_weather",
            Result = functionCallResult,
        };

        IMessage[] chatHistory = [
            new TextMessage(Role.User, "what's the weather in Philadelphia?"),
            new ToolCallMessage([toolCall], from: "assistant"),
            new ToolCallResultMessage([toolCall], from: "user" ),
        ];

        var reply = await agent.SendAsync(chatHistory: chatHistory);

        reply.Should().BeOfType<TextMessage>();
        reply.GetContent().Should().Be("The weather report for Philadelphia on 6/14/2024 is sunny.");
    }

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicAgentFunctionCallMiddlewareMessageTest()
    {
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);
        var function = new AnthropicTestFunctionCalls();
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [function.WeatherReportFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { function.WeatherReportFunctionContract.Name!, function.GetWeatherReportWrapper }
            });

        var functionCallAgent = new AnthropicClientAgent(
                client,
                name: "AnthropicAgent",
                AnthropicConstants.Claude3Haiku,
                systemMessage: "You are a helpful AI assistant.",
                tools: [AnthropicTestUtils.WeatherTool]
            )
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionCallMiddleware);

        var question = new TextMessage(Role.User, "what's the weather in Philadelphia?");
        var reply = await functionCallAgent.SendAsync(question);

        var finalReply = await functionCallAgent.SendAsync(chatHistory: [question, reply]);
        finalReply.Should().BeOfType<TextMessage>();
        finalReply.GetContent()!.ToLower().Should().Contain("sunny");
    }
}
