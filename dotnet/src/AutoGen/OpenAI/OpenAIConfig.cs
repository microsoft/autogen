// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIConfig.cs

using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public class OpenAIConfig : ILLMConfig
    {
        public OpenAIConfig(string apiKey, string modelId)
        {
            this.ApiKey = apiKey;
            this.ModelId = modelId;
        }

        public string ApiKey { get; }

        public string ModelId { get; }

        public IChatCompletion CreateChatCompletion()
        {
            throw new System.NotImplementedException();
        }
    }
}
