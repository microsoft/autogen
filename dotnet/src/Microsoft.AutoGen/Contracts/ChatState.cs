// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatState.cs

using Google.Protobuf;

namespace Microsoft.AutoGen.Contracts;

public class ChatState
    <T> where T : IMessage, new()
{
    public List<ChatHistoryItem> History { get; set; } = new();
    public T Data { get; set; } = new();
}
