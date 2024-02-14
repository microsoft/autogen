// Copyright (c) Microsoft Corporation. All rights reserved.
// KernelExtension.cs

using Microsoft.SemanticKernel;

namespace AutoGen.SemanticKernel.Extension;

public static class KernelExtension
{
    public static SemanticKernelAgent ToSemanticKernelAgent(this Kernel kernel, string name, string systemMessage = "You are a helpful AI assistant")
    {
        return new SemanticKernelAgent(kernel, name, systemMessage);
    }
}
