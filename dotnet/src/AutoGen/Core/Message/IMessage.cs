// Copyright (c) Microsoft Corporation. All rights reserved.
// Message.cs

namespace AutoGen;

public interface IMessage
{
    string? From { get; set; }
}

public interface IMessage<out T> : IMessage
{
    T Content { get; }
}
