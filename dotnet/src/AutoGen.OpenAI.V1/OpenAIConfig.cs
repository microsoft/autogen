// Copyright (c) Microsoft. All rights reserved.

namespace AutoGen.OpenAI.V1;

public class OpenAIConfig : ILLMConfig
{
    public OpenAIConfig(string apiKey, string modelId)
    {
        this.ApiKey = apiKey;
        this.ModelId = modelId;
    }

    public string ApiKey { get; }

    public string ModelId { get; }
}
