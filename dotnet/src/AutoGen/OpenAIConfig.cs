// Copyright (c) Microsoft. All rights reserved.

using OpenAI;
using OpenAI.Chat;

namespace AutoGen;

public class OpenAIConfig : ILLMConfig
{
    public OpenAIConfig(string apiKey, string modelId)
    {
        this.ApiKey = apiKey;
        this.ModelId = modelId;
    }

    public string ApiKey { get; }

    public string ModelId { get; }

    internal ChatClient CreateChatClient()
    {
        var client = new OpenAIClient(this.ApiKey);

        return client.GetChatClient(this.ModelId);
    }
}
