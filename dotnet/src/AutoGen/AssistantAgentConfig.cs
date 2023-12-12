// Copyright (c) Microsoft Corporation. All rights reserved.
// AssistantAgentConfig.cs

using System.Collections.Generic;
using Azure.AI.OpenAI;
using Microsoft.SemanticKernel.AI.ChatCompletion;

namespace AutoGen
{
    public interface ILLMConfig
    {
        IChatCompletion CreateChatCompletion();
    }

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

        public IChatCompletion CreateChatCompletion()
        {
            throw new System.NotImplementedException();
        }
    }

    public class AssistantAgentConfig
    {
        public IEnumerable<FunctionDefinition>? FunctionDefinitions { get; set; }

        public IEnumerable<ILLMConfig>? ConfigList { get; set; }

        public float? Temperature { get; set; } = 0.7f;

        public int? Timeout { get; set; }
    }
}
