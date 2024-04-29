// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIConfig.cs

namespace AutoGen.OpenAI;

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
