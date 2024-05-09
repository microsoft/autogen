// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelCodeSnippet.cs

using AutoGen.Core;
using AutoGen.SemanticKernel;
using AutoGen.SemanticKernel.Extension;
using FluentAssertions;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;

namespace AutoGen.BasicSample.CodeSnippet;

public class SemanticKernelCodeSnippet
{
    public async Task<string> GetWeather(string location)
    {
        return "The weather in " + location + " is sunny.";
    }
    public async Task CreateSemanticKernelAgentAsync()
    {
        #region create_semantic_kernel_agent
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-3.5-turbo";
        var builder = Kernel.CreateBuilder()
           .AddOpenAIChatCompletion(modelId: modelId, apiKey: openAIKey);
        var kernel = builder.Build();

        // create a semantic kernel agent
        var semanticKernelAgent = new SemanticKernelAgent(
            kernel: kernel,
            name: "assistant",
            systemMessage: "You are an assistant that help user to do some tasks.");

        // SemanticKernelAgent supports the following message types:
        // - IMessage<ChatMessageContent> where ChatMessageContent is from Azure.AI.OpenAI

        var helloMessage = new ChatMessageContent(AuthorRole.User, "Hello");

        // Use MessageEnvelope.Create to create an IMessage<ChatRequestMessage>
        var chatMessageContent = MessageEnvelope.Create(helloMessage);
        var reply = await semanticKernelAgent.SendAsync(chatMessageContent);

        // The type of reply is MessageEnvelope<ChatResponseMessage> where ChatResponseMessage is from Azure.AI.OpenAI
        reply.Should().BeOfType<MessageEnvelope<ChatMessageContent>>();

        // You can un-envelop the reply to get the ChatResponseMessage
        ChatMessageContent response = reply.As<MessageEnvelope<ChatMessageContent>>().Content;
        response.Role.Should().Be(AuthorRole.Assistant);
        #endregion create_semantic_kernel_agent

        #region create_semantic_kernel_agent_streaming
        var streamingReply = semanticKernelAgent.GenerateStreamingReplyAsync(new[] { chatMessageContent });

        await foreach (var streamingMessage in streamingReply)
        {
            streamingMessage.Should().BeOfType<MessageEnvelope<StreamingChatMessageContent>>();
            streamingMessage.As<MessageEnvelope<StreamingChatMessageContent>>().From.Should().Be("assistant");
        }
        #endregion create_semantic_kernel_agent_streaming
    }

    public async Task SemanticKernelChatMessageContentConnector()
    {
        #region register_semantic_kernel_chat_message_content_connector
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-3.5-turbo";
        var builder = Kernel.CreateBuilder()
           .AddOpenAIChatCompletion(modelId: modelId, apiKey: openAIKey);
        var kernel = builder.Build();

        // create a semantic kernel agent
        var semanticKernelAgent = new SemanticKernelAgent(
            kernel: kernel,
            name: "assistant",
            systemMessage: "You are an assistant that help user to do some tasks.");

        // Register the connector middleware to the kernel agent
        var semanticKernelAgentWithConnector = semanticKernelAgent
            .RegisterMessageConnector();

        // now semanticKernelAgentWithConnector supports more message types
        IMessage[] messages = [
            MessageEnvelope.Create(new ChatMessageContent(AuthorRole.User, "Hello")),
            new TextMessage(Role.Assistant, "Hello", from: "user"),
            new MultiModalMessage(Role.Assistant,
                [
                    new TextMessage(Role.Assistant, "Hello", from: "user"),
                ],
                from: "user"),
        ];

        foreach (var message in messages)
        {
            var reply = await semanticKernelAgentWithConnector.SendAsync(message);

            // SemanticKernelChatMessageContentConnector will convert the reply message to TextMessage
            reply.Should().BeOfType<TextMessage>();
        }
        #endregion register_semantic_kernel_chat_message_content_connector
    }
}
