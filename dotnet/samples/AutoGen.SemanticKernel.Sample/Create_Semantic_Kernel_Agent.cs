// Copyright (c) Microsoft Corporation. All rights reserved.
// Create_Semantic_Kernel_Agent.cs

using AutoGen.Core;
using AutoGen.SemanticKernel.Extension;
using Microsoft.SemanticKernel;

namespace AutoGen.SemanticKernel.Sample;

public class Create_Semantic_Kernel_Agent
{
    public static async Task RunAsync()
    {
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-3.5-turbo";
        var kernel = Kernel.CreateBuilder()
            .AddOpenAIChatCompletion(modelId: modelId, apiKey: openAIKey)
            .Build();

        var skAgent = new SemanticKernelAgent(
            kernel: kernel,
            name: "assistant",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector() // register message connector so it support AutoGen built-in message types like TextMessage.
            .RegisterPrintMessage(); // pretty print the message to the console

        await skAgent.SendAsync("Hey tell me a long tedious joke");
    }
}
