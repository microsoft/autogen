// Copyright (c) Microsoft Corporation. All rights reserved.
// KernelExtension.cs

using Microsoft.SemanticKernel.Agents;

namespace AutoGen.SemanticKernel.Extension;

public static class KernelExtension
{
    public static SemanticKernelAgent ToSemanticKernelAgent(this ChatCompletionAgent agent, string name, string systemMessage = "You are a helpful AI assistant")
    {
        return new SemanticKernelAgent(agent, name, systemMessage);
    }
}
