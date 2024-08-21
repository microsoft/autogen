// Copyright (c) Microsoft Corporation. All rights reserved.
// AzureOpenAIConfig.cs

using OpenAI;
using OpenAI.Chat;

namespace AutoGen;

public class AzureOpenAIConfig : ILLMConfig
{
    public AzureOpenAIConfig(string endpoint, string deploymentName, string apiKey, string? modelId = null)
    {
        this.Endpoint = endpoint;
        this.DeploymentName = deploymentName;
        this.ApiKey = apiKey;
        this.ModelId = modelId;
    }

    public string Endpoint { get; }

    public string DeploymentName { get; }

    public string ApiKey { get; }

    public string? ModelId { get; }

    internal ChatClient CreateChatClient()
    {
        var client = new OpenAIClient(new System.ClientModel.ApiKeyCredential(this.ApiKey), new OpenAIClientOptions
        {
            Endpoint = new System.Uri(this.Endpoint),
        });

        return client.GetChatClient(DeploymentName);
    }
}
