// Copyright (c) Microsoft Corporation. All rights reserved.
// Example09_SemanticKernel.cs

using Microsoft.SemanticKernel;
using AutoGen.SemanticKernel.Extension;
namespace AutoGen.BasicSample;

public class Example09_SemanticKernel
{
    public static async Task RunAsync()
    {
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-3.5-turbo";
        var kernel = Kernel.CreateBuilder()
            .AddOpenAIChatCompletion(modelId: modelId, apiKey: openAIKey)
            .Build();

        var skAgent = kernel.ToSemanticKernelAgent(name: "skAgent", systemMessage: "You are a helpful AI assistant")
            .RegisterPrintFormatMessageHook();

        var userProxyAgent = new UserProxyAgent(name: "user", humanInputMode: ConversableAgent.HumanInputMode.ALWAYS);

        await userProxyAgent.InitiateChatAsync(
            receiver: skAgent,
            message: "Hey assistant, please help me to do some tasks.",
            maxRound: 10);
    }

}
