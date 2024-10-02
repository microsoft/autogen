// Copyright (c) Microsoft Corporation. All rights reserved.
// AzureOpenAIConfig.cs

using Azure.AI.OpenAI;
using OpenAI.Chat;

namespace AutoGen;

public class AzureOpenAIConfig : ILLMConfig
{
    public AzureOpenAIConfig(string endpoint, string deploymentName, string apiKey)
    {
        this.Endpoint = endpoint;
        this.DeploymentName = deploymentName;
        this.ApiKey = apiKey;
    }

    public string Endpoint { get; }

    public string DeploymentName { get; }

    public string ApiKey { get; }

    internal ChatClient CreateChatClient()
    {
        var client = new AzureOpenAIClient(new System.Uri(this.Endpoint), this.ApiKey);

        return client.GetChatClient(DeploymentName);
    }
}
