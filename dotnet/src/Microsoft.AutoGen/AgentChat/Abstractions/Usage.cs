// Copyright (c) Microsoft Corporation. All rights reserved.
// Usage.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public struct RequestUsage
{
    public int PromptTokens { get; set; }
    public int CompletionTokens { get; set; }
}
