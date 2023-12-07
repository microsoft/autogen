// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentConfig.cs

using System.Collections.Generic;
using Azure.AI.OpenAI;

namespace AutoGen
{
    public interface ILLMConfig
    {
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
    }

    public class AgentConfig
    {
        public IEnumerable<FunctionDefinition>? FunctionDefinitions { get; set; }

        //public IEnumerable<ILLMConfig>
    }
}
