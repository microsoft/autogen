// Copyright (c) Microsoft Corporation. All rights reserved.
// Example01_AssistantAgent.cs

using AutoGen;
using AutoGen.BasicSample;
using AutoGen.Core;

/// <summary>
/// This example shows the basic usage of <see cref="ConversableAgent"/> class.
/// </summary>
public static class Example_AssistantAgent
{
    public static async Task RunAsync()
    {
        var gpt35 = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var config = new ConversableAgentConfig
        {
            Temperature = 0,
            ConfigList = [gpt35],
        };

        // create assistant agent
        var aiAssistant = new AssistantAgent(
            name: "assistant",
            systemMessage: @"You are an assistant that help user to do some tasks. 
                            You specialise in property within the UK and have been working in the industry for 20 years.
                            You have a friendly and professional communication style",
            llmConfig: config);

        var newMessage = "hey";
        if (!string.IsNullOrWhiteSpace(newMessage))
        {
            //ask question
            var reply = await aiAssistant.SendAsync(newMessage);
        }
    }
}
