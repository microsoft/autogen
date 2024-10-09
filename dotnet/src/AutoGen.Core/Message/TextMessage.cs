// Copyright (c) Microsoft Corporation. All rights reserved.
// TextMessage.cs

namespace AutoGen.Core;

public class TextMessage : IMessage, ICanGetTextContent
{
    public TextMessage(Role role, string content, string? from = null)
    {
        this.Content = content;
        this.Role = role;
        this.From = from;
    }

    public TextMessage(TextMessageUpdate update)
    {
        this.Content = update.Content ?? string.Empty;
        this.Role = update.Role;
        this.From = update.From;
    }

    public void Update(TextMessageUpdate update)
    {
        if (update.Role != this.Role)
        {
            throw new System.ArgumentException("Role mismatch", nameof(update));
        }

        if (update.From != this.From)
        {
            throw new System.ArgumentException("From mismatch", nameof(update));
        }

        this.Content = this.Content + update.Content ?? string.Empty;
    }

    public Role Role { get; set; }

    public string Content { get; set; }

    public string? From { get; set; }

    public override string ToString()
    {
        return $"TextMessage({this.Role}, {this.Content}, {this.From})";
    }

    public string? GetContent()
    {
        return this.Content;
    }
}

public class TextMessageUpdate : IMessage, ICanGetTextContent
{
    public TextMessageUpdate(Role role, string? content, string? from = null)
    {
        this.Content = content;
        this.From = from;
        this.Role = role;
    }

    public string? Content { get; set; }

    public string? From { get; set; }

    public Role Role { get; set; }

    public string? GetContent()
    {
        return this.Content;
    }
}
