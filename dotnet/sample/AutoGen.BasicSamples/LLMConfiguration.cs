// Copyright (c) Microsoft Corporation. All rights reserved.
// LLMConfiguration.cs

using OpenAI;
using OpenAI.Chat;

namespace AutoGen.BasicSample;

internal static class LLMConfiguration
{
    public static ChatClient GetOpenAIGPT4o_mini()
    {
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-4o-mini";

        return new OpenAIClient(openAIKey).GetChatClient(modelId);
    }

    public static AzureOpenAIConfig GetAzureOpenAIGPT3_5_Turbo(string? deployName = null)
    {
        var azureOpenAIKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        deployName = deployName ?? Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        return new AzureOpenAIConfig(endpoint, deployName, azureOpenAIKey);
    }
}
