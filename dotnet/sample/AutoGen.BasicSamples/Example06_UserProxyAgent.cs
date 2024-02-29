// Copyright (c) Microsoft Corporation. All rights reserved.
// Example06_UserProxyAgent.cs
using autogen = AutoGen.LLMConfigAPI;

namespace AutoGen.BasicSample;

public static class Example06_UserProxyAgent
{
    public static async Task RunAsync()
    {
        // get OpenAI Key and create config
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var llmConfig = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-3.5-turbo" });
        var config = new ConversableAgentConfig
        {
            Temperature = 0,
            ConfigList = llmConfig,
        };

        var assistantAgent = new AssistantAgent(
            name: "assistant",
            systemMessage: "You are an assistant that help user to do some tasks.",
            llmConfig: config)
            .RegisterPrintFormatMessageHook();

        // set human input mode to ALWAYS so that user always provide input
        var userProxyAgent = new UserProxyAgent(
            name: "user",
            humanInputMode: HumanInputMode.ALWAYS)
            .RegisterPrintFormatMessageHook();

        // start the conversation
        await userProxyAgent.InitiateChatAsync(
            receiver: assistantAgent,
            message: "Hey assistant, please help me to do some tasks.",
            maxRound: 10);
    }
}
