// Copyright (c) Microsoft Corporation. All rights reserved.
// Create_Semantic_Kernel_Chat_Agent.cs

using AutoGen.Core;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Agents;

namespace AutoGen.SemanticKernel.Sample;

public class Create_Semantic_Kernel_Chat_Agent
{
    public static async Task RunAsync()
    {
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-3.5-turbo";
        var kernel = Kernel.CreateBuilder()
            .AddOpenAIChatCompletion(modelId: modelId, apiKey: openAIKey)
            .Build();

        // The built-in ChatCompletionAgent from semantic kernel.
        var chatAgent = new ChatCompletionAgent()
        {
            Kernel = kernel,
            Name = "assistant",
            Description = "You are a helpful AI assistant",
        };

        var messageConnector = new SemanticKernelChatMessageContentConnector();
        var skAgent = new SemanticKernelChatCompletionAgent(chatAgent)
            .RegisterMiddleware(messageConnector) // register message connector so it support AutoGen built-in message types like TextMessage.
            .RegisterPrintMessage(); // pretty print the message to the console

        await skAgent.SendAsync("Hey tell me a long tedious joke");
    }
}
