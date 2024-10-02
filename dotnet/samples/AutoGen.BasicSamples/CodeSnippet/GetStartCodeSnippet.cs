// Copyright (c) Microsoft Corporation. All rights reserved.
// GetStartCodeSnippet.cs

#region snippet_GetStartCodeSnippet
using AutoGen;
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using OpenAI;
#endregion snippet_GetStartCodeSnippet

public class GetStartCodeSnippet
{
    public async Task CodeSnippet1()
    {
        #region code_snippet_1
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var openAIClient = new OpenAIClient(openAIKey);
        var model = "gpt-4o-mini";

        var assistantAgent = new OpenAIChatAgent(
            name: "assistant",
            systemMessage: "You are an assistant that help user to do some tasks.",
            chatClient: openAIClient.GetChatClient(model))
            .RegisterMessageConnector()
            .RegisterPrintMessage(); // register a hook to print message nicely to console

        // set human input mode to ALWAYS so that user always provide input
        var userProxyAgent = new UserProxyAgent(
            name: "user",
            humanInputMode: HumanInputMode.ALWAYS)
            .RegisterPrintMessage();

        // start the conversation
        await userProxyAgent.InitiateChatAsync(
            receiver: assistantAgent,
            message: "Hey assistant, please do me a favor.",
            maxRound: 10);
        #endregion code_snippet_1
    }
}
