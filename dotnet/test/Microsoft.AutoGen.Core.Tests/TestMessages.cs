// Copyright (c) Microsoft Corporation. All rights reserved.
// TestMessages.cs

namespace Microsoft.AutoGen.Core.Tests;

public class TextMessage
{
    public string Source { get; set; } = "";
    public string Content { get; set; } = "";
}

public class RpcTextMessage
{
    public string Source { get; set; } = "";
    public string Content { get; set; } = "";
}

public sealed class BasicMessage
{
    public string Content { get; set; } = string.Empty;
}

