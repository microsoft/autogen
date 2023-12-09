// Copyright (c) Microsoft Corporation. All rights reserved.
// Example01_AssistantAgent.cs

using AutoGen;
using FluentAssertions;
using Microsoft.SemanticKernel.AI.ChatCompletion;
using autogen = AutoGen.API;
/// <summary>
/// This example shows the basic usage of <see cref="AssistantAgent"/> class.
/// </summary>
public static class Example01_AssistantAgent
{
    public static async Task RunAsync()
    {
        // get OpenAI Key and create config
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var llmConfig = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-3.5-turbo" });
        var config = new AssistantAgentConfig
        {
            Temperature = 0,
            ConfigList = llmConfig,
        };

        // create assistant agent
        var assistantAgent = new AssistantAgent(
            name: "assistant",
            systemMessage: "You convert what user said to all uppercase.",
            llmConfig: config);

        // talk to the assistant agent
        var reply = await assistantAgent.SendAsync("hello world");
        reply.Content?.Should().Be("HELLO WORLD");

        // to carry on the conversation, pass the previous conversation history to the next call
        var conversationHistory = new List<Message>
        {
            new Message(AuthorRole.User, "hello world"), // first message
            reply, // reply from assistant agent
        };

        reply = await assistantAgent.SendAsync("hello world again", conversationHistory);
        reply.Content?.Should().Be("HELLO WORLD AGAIN");
    }
}
