// Copyright (c) Microsoft Corporation. All rights reserved.
// KernelExtension.cs

using System;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Agents;

namespace AutoGen.SemanticKernel.Extension;

public static class KernelExtension
{
    [Obsolete("This API will be removed. Use ToSemanticKernelAgent overload with ChatCompletionAgent instead of Kernel")]
    public static SemanticKernelAgent ToSemanticKernelAgent(this Kernel kernel, string name, string systemMessage = "You are a helpful AI assistant", PromptExecutionSettings? settings = null)
    {
        return new SemanticKernelAgent(kernel, name, systemMessage, settings);
    }

    public static SemanticKernelAgent ToSemanticKernelAgent(this ChatCompletionAgent agent, string name, string systemMessage = "You are a helpful AI assistant")
    {
        return new SemanticKernelAgent(agent, name, systemMessage);
    }
}
