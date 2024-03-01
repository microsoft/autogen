// Copyright (c) Microsoft Corporation. All rights reserved.
// TextMessage.cs

namespace AutoGen.Core;

public class TextMessage : IMessage
{
    public TextMessage(Role role, string content, string? from = null)
    {
        this.Content = content;
        this.Role = role;
        this.From = from;
    }

    public Role Role { get; set; }

    public string Content { get; set; }

    public string? From { get; set; }

    public override string ToString()
    {
        return $"TextMessage({this.Role}, {this.Content}, {this.From})";
    }
}
