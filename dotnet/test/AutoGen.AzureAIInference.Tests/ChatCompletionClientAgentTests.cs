// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatCompletionClientAgentTests.cs

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using AutoGen.AzureAIInference.Extension;
using AutoGen.Core;
using AutoGen.Tests;
using Azure.AI.Inference;
using FluentAssertions;
using Xunit;

namespace AutoGen.AzureAIInference.Tests;

[Trait("Category", "UnitV1")]
public partial class ChatCompletionClientAgentTests
{
    /// <summary>
    /// Get the weather for a location.
    /// </summary>
    /// <param name="location">location</param>
    /// <returns></returns>
    [Function]
    public async Task<string> GetWeatherAsync(string location)
    {
        return $"The weather in {location} is sunny.";
    }

    [ApiKeyFact("GH_API_KEY")]
    public async Task ChatCompletionAgent_LLaMA3_1()
    {
        var client = CreateChatCompletionClient();
        var model = "meta-llama-3-8b-instruct";

        var agent = new ChatCompletionsClientAgent(client, "assistant", model)
            .RegisterMessageConnector();

        var reply = await this.BasicChatAsync(agent);
        reply.Should().BeOfType<TextMessage>();

        reply = await this.BasicChatWithContinuousMessageFromSameSenderAsync(agent);
        reply.Should().BeOfType<TextMessage>();
    }

    [ApiKeyFact("GH_API_KEY")]
    public async Task BasicConversation_Mistra_Small()
    {
        var deployName = "Mistral-small";
        var client = CreateChatCompletionClient();
        var openAIChatAgent = new ChatCompletionsClientAgent(
            chatCompletionsClient: client,
            name: "assistant",
            modelName: deployName);

        // By default, ChatCompletionClientAgent supports the following message types
        // - IMessage<ChatRequestMessage>
        var chatMessageContent = MessageEnvelope.Create(new ChatRequestUserMessage("Hello"));
        var reply = await openAIChatAgent.SendAsync(chatMessageContent);

        reply.Should().BeOfType<MessageEnvelope<ChatCompletions>>();
        reply.As<MessageEnvelope<ChatCompletions>>().From.Should().Be("assistant");
        reply.As<MessageEnvelope<ChatCompletions>>().Content.Choices.First().Message.Role.Should().Be(ChatRole.Assistant);
        reply.As<MessageEnvelope<ChatCompletions>>().Content.Usage.TotalTokens.Should().BeGreaterThan(0);

        // test streaming
        var streamingReply = openAIChatAgent.GenerateStreamingReplyAsync(new[] { chatMessageContent });

        await foreach (var streamingMessage in streamingReply)
        {
            streamingMessage.Should().BeOfType<MessageEnvelope<StreamingChatCompletionsUpdate>>();
            streamingMessage.As<MessageEnvelope<StreamingChatCompletionsUpdate>>().From.Should().Be("assistant");
        }
    }

    [ApiKeyFact("GH_API_KEY")]
    public async Task ChatCompletionsMessageContentConnector_Phi3_Mini()
    {
        var deployName = "Phi-3-mini-4k-instruct";
        var openaiClient = CreateChatCompletionClient();
        var chatCompletionAgent = new ChatCompletionsClientAgent(
            chatCompletionsClient: openaiClient,
            name: "assistant",
            modelName: deployName);

        MiddlewareStreamingAgent<ChatCompletionsClientAgent> assistant = chatCompletionAgent
            .RegisterMessageConnector();

        var messages = new IMessage[]
        {
            MessageEnvelope.Create(new ChatRequestUserMessage("Hello")),
            new TextMessage(Role.Assistant, "Hello", from: "user"),
            new MultiModalMessage(Role.Assistant,
                [
                    new TextMessage(Role.Assistant, "Hello", from: "user"),
                ],
                from: "user"),
        };

        foreach (var message in messages)
        {
            var reply = await assistant.SendAsync(message);

            reply.Should().BeOfType<TextMessage>();
            reply.As<TextMessage>().From.Should().Be("assistant");
        }

        // test streaming
        foreach (var message in messages)
        {
            var reply = assistant.GenerateStreamingReplyAsync([message]);

            await foreach (var streamingMessage in reply)
            {
                streamingMessage.Should().BeOfType<TextMessageUpdate>();
                streamingMessage.As<TextMessageUpdate>().From.Should().Be("assistant");
            }
        }
    }

    [ApiKeyFact("GH_API_KEY")]
    public async Task ChatCompletionClientAgentToolCall_Mistral_Nemo()
    {
        var deployName = "Mistral-nemo";
        var chatCompletionClient = CreateChatCompletionClient();
        var agent = new ChatCompletionsClientAgent(
            chatCompletionsClient: chatCompletionClient,
            name: "assistant",
            modelName: deployName);

        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [this.GetWeatherAsyncFunctionContract]);
        MiddlewareStreamingAgent<ChatCompletionsClientAgent> assistant = agent
            .RegisterMessageConnector();

        assistant.StreamingMiddlewares.Count().Should().Be(1);
        var functionCallAgent = assistant
            .RegisterStreamingMiddleware(functionCallMiddleware);

        var question = "What's the weather in Seattle";
        var messages = new IMessage[]
        {
            MessageEnvelope.Create(new ChatRequestUserMessage(question)),
            new TextMessage(Role.Assistant, question, from: "user"),
            new MultiModalMessage(Role.Assistant,
                [
                    new TextMessage(Role.Assistant, question, from: "user"),
                ],
                from: "user"),
        };

        foreach (var message in messages)
        {
            var reply = await functionCallAgent.SendAsync(message);

            reply.Should().BeOfType<ToolCallMessage>();
            reply.As<ToolCallMessage>().From.Should().Be("assistant");
            reply.As<ToolCallMessage>().ToolCalls.Count().Should().Be(1);
            reply.As<ToolCallMessage>().ToolCalls.First().FunctionName.Should().Be(this.GetWeatherAsyncFunctionContract.Name);
        }

        // test streaming
        foreach (var message in messages)
        {
            var reply = functionCallAgent.GenerateStreamingReplyAsync([message]);
            ToolCallMessage? toolCallMessage = null;
            await foreach (var streamingMessage in reply)
            {
                streamingMessage.Should().BeOfType<ToolCallMessageUpdate>();
                streamingMessage.As<ToolCallMessageUpdate>().From.Should().Be("assistant");
                if (toolCallMessage is null)
                {
                    toolCallMessage = new ToolCallMessage(streamingMessage.As<ToolCallMessageUpdate>());
                }
                else
                {
                    toolCallMessage.Update(streamingMessage.As<ToolCallMessageUpdate>());
                }
            }

            toolCallMessage.Should().NotBeNull();
            toolCallMessage!.From.Should().Be("assistant");
            toolCallMessage.ToolCalls.Count().Should().Be(1);
            toolCallMessage.ToolCalls.First().FunctionName.Should().Be(this.GetWeatherAsyncFunctionContract.Name);
        }
    }

    [ApiKeyFact("GH_API_KEY")]
    public async Task ChatCompletionClientAgentToolCallInvoking_gpt_4o_mini()
    {
        var deployName = "gpt-4o-mini";
        var client = CreateChatCompletionClient();
        var agent = new ChatCompletionsClientAgent(
            chatCompletionsClient: client,
            name: "assistant",
            modelName: deployName);

        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [this.GetWeatherAsyncFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>> { { this.GetWeatherAsyncFunctionContract.Name!, this.GetWeatherAsyncWrapper } });
        MiddlewareStreamingAgent<ChatCompletionsClientAgent> assistant = agent
            .RegisterMessageConnector();

        var functionCallAgent = assistant
            .RegisterStreamingMiddleware(functionCallMiddleware);

        var question = "What's the weather in Seattle";
        var messages = new IMessage[]
        {
            MessageEnvelope.Create(new ChatRequestUserMessage(question)),
            new TextMessage(Role.Assistant, question, from: "user"),
            new MultiModalMessage(Role.Assistant,
                [
                    new TextMessage(Role.Assistant, question, from: "user"),
                ],
                from: "user"),
        };

        foreach (var message in messages)
        {
            var reply = await functionCallAgent.SendAsync(message);

            reply.Should().BeOfType<ToolCallAggregateMessage>();
            reply.From.Should().Be("assistant");
            reply.GetToolCalls()!.Count().Should().Be(1);
            reply.GetToolCalls()!.First().FunctionName.Should().Be(this.GetWeatherAsyncFunctionContract.Name);
            reply.GetContent()!.ToLower().Should().Contain("seattle");
        }

        // test streaming
        foreach (var message in messages)
        {
            var reply = functionCallAgent.GenerateStreamingReplyAsync([message]);
            await foreach (var streamingMessage in reply)
            {
                if (streamingMessage is not IMessage)
                {
                    streamingMessage.Should().BeOfType<ToolCallMessageUpdate>();
                    streamingMessage.As<ToolCallMessageUpdate>().From.Should().Be("assistant");
                }
                else
                {
                    streamingMessage.Should().BeOfType<ToolCallAggregateMessage>();
                    streamingMessage.As<IMessage>().GetContent()!.ToLower().Should().Contain("seattle");
                }
            }
        }
    }

    [ApiKeyFact("GH_API_KEY")]
    public async Task ItCreateChatCompletionClientAgentWithChatCompletionOption_AI21_Jamba_Instruct()
    {
        var deployName = "AI21-Jamba-Instruct";
        var chatCompletionsClient = CreateChatCompletionClient();
        var options = new ChatCompletionsOptions()
        {
            Model = deployName,
            Temperature = 0.7f,
            MaxTokens = 1,
        };

        var openAIChatAgent = new ChatCompletionsClientAgent(
            chatCompletionsClient: chatCompletionsClient,
            name: "assistant",
            options: options)
            .RegisterMessageConnector();

        var respond = await openAIChatAgent.SendAsync("hello");
        respond.GetContent()?.Should().NotBeNullOrEmpty();
    }

    [Fact]
    public async Task ItThrowExceptionWhenChatCompletionOptionContainsMessages()
    {
        var client = new ChatCompletionsClient(new Uri("https://dummy.com"), new Azure.AzureKeyCredential("dummy"));
        var options = new ChatCompletionsOptions([new ChatRequestUserMessage("hi")])
        {
            Model = "dummy",
            Temperature = 0.7f,
            MaxTokens = 1,
        };

        var action = () => new ChatCompletionsClientAgent(
            chatCompletionsClient: client,
            name: "assistant",
            options: options)
            .RegisterMessageConnector();

        action.Should().ThrowExactly<ArgumentException>().WithMessage("Messages should not be provided in options");
    }

    private ChatCompletionsClient CreateChatCompletionClient()
    {
        var apiKey = Environment.GetEnvironmentVariable("GH_API_KEY") ?? throw new Exception("Please set GH_API_KEY environment variable.");
        var endpoint = "https://models.inference.ai.azure.com";
        return new ChatCompletionsClient(new Uri(endpoint), new Azure.AzureKeyCredential(apiKey));
    }

    /// <summary>
    /// The agent should return a text message based on the chat history.
    /// </summary>
    /// <param name="agent"></param>
    /// <returns></returns>
    private async Task<IMessage> BasicChatEndWithSelfMessageAsync(IAgent agent)
    {
        IMessage[] chatHistory = [
            new TextMessage(Role.Assistant, "Hello", from: "user"),
            new TextMessage(Role.Assistant, "Hello", from: "user2"),
            new TextMessage(Role.Assistant, "Hello", from: "user3"),
            new TextMessage(Role.Assistant, "Hello", from: agent.Name),
        ];

        return await agent.GenerateReplyAsync(chatHistory);
    }

    /// <summary>
    /// The agent should return a text message based on the chat history.
    /// </summary>
    /// <param name="agent"></param>
    /// <returns></returns>
    private async Task<IMessage> BasicChatAsync(IAgent agent)
    {
        IMessage[] chatHistory = [
            new TextMessage(Role.Assistant, "Hello", from: agent.Name),
            new TextMessage(Role.Assistant, "Hello", from: "user"),
            new TextMessage(Role.Assistant, "Hello", from: "user1"),
        ];

        return await agent.GenerateReplyAsync(chatHistory);
    }

    /// <summary>
    /// The agent should return a text message based on the chat history. This test the generate reply with continuous message from the same sender.
    /// </summary>
    private async Task<IMessage> BasicChatWithContinuousMessageFromSameSenderAsync(IAgent agent)
    {
        IMessage[] chatHistory = [
            new TextMessage(Role.Assistant, "Hello", from: "user"),
            new TextMessage(Role.Assistant, "Hello", from: "user"),
            new TextMessage(Role.Assistant, "Hello", from: agent.Name),
            new TextMessage(Role.Assistant, "Hello", from: agent.Name),
        ];

        return await agent.GenerateReplyAsync(chatHistory);
    }

    /// <summary>
    /// The agent should return a text message based on the chat history.
    /// </summary>
    /// <param name="agent"></param>
    /// <returns></returns>
    private async Task<IMessage> ImageChatAsync(IAgent agent)
    {
        var image = Path.Join("testData", "images", "square.png");
        var binaryData = File.ReadAllBytes(image);
        var imageMessage = new ImageMessage(Role.Assistant, BinaryData.FromBytes(binaryData, "image/png"), from: "user");

        IMessage[] chatHistory = [
            imageMessage,
            new TextMessage(Role.Assistant, "What's in the picture", from: "user"),
        ];

        return await agent.GenerateReplyAsync(chatHistory);
    }

    /// <summary>
    /// The agent should return a text message based on the chat history. This test the generate reply with continuous image messages.
    /// </summary>
    /// <param name="agent"></param>
    /// <returns></returns>
    private async Task<IMessage> MultipleImageChatAsync(IAgent agent)
    {
        var image1 = Path.Join("testData", "images", "square.png");
        var image2 = Path.Join("testData", "images", "background.png");
        var binaryData1 = File.ReadAllBytes(image1);
        var binaryData2 = File.ReadAllBytes(image2);
        var imageMessage1 = new ImageMessage(Role.Assistant, BinaryData.FromBytes(binaryData1, "image/png"), from: "user");
        var imageMessage2 = new ImageMessage(Role.Assistant, BinaryData.FromBytes(binaryData2, "image/png"), from: "user");

        IMessage[] chatHistory = [
            imageMessage1,
            imageMessage2,
            new TextMessage(Role.Assistant, "What's in the picture", from: "user"),
        ];

        return await agent.GenerateReplyAsync(chatHistory);
    }

    /// <summary>
    /// The agent should return a text message based on the chat history.
    /// </summary>
    /// <param name="agent"></param>
    /// <returns></returns>
    private async Task<IMessage> MultiModalChatAsync(IAgent agent)
    {
        var image = Path.Join("testData", "images", "square.png");
        var binaryData = File.ReadAllBytes(image);
        var question = "What's in the picture";
        var imageMessage = new ImageMessage(Role.Assistant, BinaryData.FromBytes(binaryData, "image/png"), from: "user");
        var textMessage = new TextMessage(Role.Assistant, question, from: "user");

        IMessage[] chatHistory = [
            new MultiModalMessage(Role.Assistant, [imageMessage, textMessage], from: "user"),
        ];

        return await agent.GenerateReplyAsync(chatHistory);
    }

    /// <summary>
    /// The agent should return a tool call message based on the chat history.
    /// </summary>
    /// <param name="agent"></param>
    /// <returns></returns>
    private async Task<IMessage> ToolCallChatAsync(IAgent agent)
    {
        var question = "What's the weather in Seattle";
        var messages = new IMessage[]
        {
            new TextMessage(Role.Assistant, question, from: "user"),
        };

        return await agent.GenerateReplyAsync(messages);
    }

    /// <summary>
    /// The agent should throw an exception because tool call result is not available.
    /// </summary>
    private async Task<IMessage> ToolCallFromSelfChatAsync(IAgent agent)
    {
        var question = "What's the weather in Seattle";
        var messages = new IMessage[]
        {
            new TextMessage(Role.Assistant, question, from: "user"),
            new ToolCallMessage("GetWeatherAsync", "Seattle", from: agent.Name),
        };

        return await agent.GenerateReplyAsync(messages);
    }

    /// <summary>
    /// mimic the further chat after tool call. The agent should return a text message based on the tool call result.
    /// </summary>
    private async Task<IMessage> ToolCallWithResultChatAsync(IAgent agent)
    {
        var question = "What's the weather in Seattle";
        var messages = new IMessage[]
        {
            new TextMessage(Role.Assistant, question, from: "user"),
            new ToolCallMessage("GetWeatherAsync", "Seattle", from: "user"),
            new ToolCallResultMessage("sunny", "GetWeatherAsync", "Seattle", from: agent.Name),
        };

        return await agent.GenerateReplyAsync(messages);
    }

    /// <summary>
    /// the agent should return a text message based on the tool call result.
    /// </summary>
    /// <param name="agent"></param>
    /// <returns></returns>
    private async Task<IMessage> AggregateToolCallFromSelfChatAsync(IAgent agent)
    {
        var textMessage = new TextMessage(Role.Assistant, "What's the weather in Seattle", from: "user");
        var toolCallMessage = new ToolCallMessage("GetWeatherAsync", "Seattle", from: agent.Name);
        var toolCallResultMessage = new ToolCallResultMessage("sunny", "GetWeatherAsync", "Seattle", from: agent.Name);
        var aggregateToolCallMessage = new ToolCallAggregateMessage(toolCallMessage, toolCallResultMessage, from: agent.Name);

        var messages = new IMessage[]
        {
            textMessage,
            aggregateToolCallMessage,
        };

        return await agent.GenerateReplyAsync(messages);
    }

    /// <summary>
    /// the agent should return a text message based on the tool call result. Because the aggregate tool call message is from other, the message would be treated as an ordinary text message.
    /// </summary>
    private async Task<IMessage> AggregateToolCallFromOtherChatWithContinuousMessageAsync(IAgent agent)
    {
        var textMessage = new TextMessage(Role.Assistant, "What's the weather in Seattle", from: "user");
        var toolCallMessage = new ToolCallMessage("GetWeatherAsync", "Seattle", from: "other");
        var toolCallResultMessage = new ToolCallResultMessage("sunny", "GetWeatherAsync", "Seattle", from: "other");
        var aggregateToolCallMessage = new ToolCallAggregateMessage(toolCallMessage, toolCallResultMessage, "other");

        var messages = new IMessage[]
        {
            textMessage,
            aggregateToolCallMessage,
        };

        return await agent.GenerateReplyAsync(messages);
    }

    /// <summary>
    /// The agent should throw an exception because tool call message from other is not allowed.
    /// </summary>
    private async Task<IMessage> ToolCallMessaageFromOtherChatAsync(IAgent agent)
    {
        var textMessage = new TextMessage(Role.Assistant, "What's the weather in Seattle", from: "user");
        var toolCallMessage = new ToolCallMessage("GetWeatherAsync", "Seattle", from: "other");

        var messages = new IMessage[]
        {
            textMessage,
            toolCallMessage,
        };

        return await agent.GenerateReplyAsync(messages);
    }

    /// <summary>
    /// The agent should throw an exception because multi-modal message from self is not allowed.
    /// </summary>
    /// <param name="agent"></param>
    /// <returns></returns>
    private async Task<IMessage> MultiModalMessageFromSelfChatAsync(IAgent agent)
    {
        var image = Path.Join("testData", "images", "square.png");
        var binaryData = File.ReadAllBytes(image);
        var question = "What's in the picture";
        var imageMessage = new ImageMessage(Role.Assistant, BinaryData.FromBytes(binaryData, "image/png"), from: agent.Name);
        var textMessage = new TextMessage(Role.Assistant, question, from: agent.Name);

        IMessage[] chatHistory = [
            new MultiModalMessage(Role.Assistant, [imageMessage, textMessage], from: agent.Name),
        ];

        return await agent.GenerateReplyAsync(chatHistory);
    }
}
