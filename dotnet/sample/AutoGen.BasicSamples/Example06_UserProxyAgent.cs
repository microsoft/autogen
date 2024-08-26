// Copyright (c) Microsoft Corporation. All rights reserved.
// Example06_UserProxyAgent.cs
using AutoGen.Core;
using AutoGen.OpenAI.V1;

namespace AutoGen.BasicSample;

public static class Example06_UserProxyAgent
{
    public static async Task RunAsync()
    {
        var gpt35 = LLMConfiguration.GetOpenAIGPT3_5_Turbo();

        var assistantAgent = new GPTAgent(
            name: "assistant",
            systemMessage: "You are an assistant that help user to do some tasks.",
            config: gpt35)
            .RegisterPrintMessage();

        // set human input mode to ALWAYS so that user always provide input
        var userProxyAgent = new UserProxyAgent(
            name: "user",
            humanInputMode: HumanInputMode.ALWAYS)
            .RegisterPrintMessage();

        // start the conversation
        await userProxyAgent.InitiateChatAsync(
            receiver: assistantAgent,
            message: "Hey assistant, please help me to do some tasks.",
            maxRound: 10);
    }
}
