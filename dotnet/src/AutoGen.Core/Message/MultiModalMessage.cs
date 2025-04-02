// Copyright (c) Microsoft Corporation. All rights reserved.
// MultiModalMessage.cs

using System;
using System.Collections.Generic;

namespace AutoGen.Core;

public class MultiModalMessage : IMessage
{
    public MultiModalMessage(Role role, IEnumerable<IMessage> content, string? from = null)
    {
        this.Role = role;
        this.Content = content;
        this.From = from;
        this.Validate();
    }

    public Role Role { get; set; }

    public IEnumerable<IMessage> Content { get; set; }

    public string? From { get; set; }

    private void Validate()
    {
        foreach (var message in this.Content)
        {
            if (message.From != this.From)
            {
                var reason = $"The from property of the message {message} is different from the from property of the aggregate message {this}";
                throw new ArgumentException($"Invalid aggregate message {reason}");
            }
        }

        // all message must be either text or image
        foreach (var message in this.Content)
        {
            if (message is not TextMessage && message is not ImageMessage)
            {
                var reason = $"The message {message} is not a text or image message";
                throw new ArgumentException($"Invalid aggregate message {reason}");
            }
        }
    }

    public override string ToString()
    {
        var stringBuilder = new System.Text.StringBuilder();
        stringBuilder.Append($"MultiModalMessage({this.Role}, {this.From})");
        foreach (var message in this.Content)
        {
            stringBuilder.Append($"\n\t{message}");
        }

        return stringBuilder.ToString();
    }
}
