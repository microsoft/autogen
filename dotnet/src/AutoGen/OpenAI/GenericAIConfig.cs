// Copyright (c) Microsoft Corporation. All rights reserved.
// GenericAIConfig.cs

namespace AutoGen.OpenAI;

public class GenericAIConfig : ILLMConfig
{
    public GenericAIConfig(string endpoint, string apiKey, string? modelId = null)
    {
        this.Endpoint = endpoint;
        this.ApiKey = apiKey;
        this.ModelId = modelId;
    }

    public string Endpoint { get; }


    public string ApiKey { get; }

    public string? ModelId { get; }
}
