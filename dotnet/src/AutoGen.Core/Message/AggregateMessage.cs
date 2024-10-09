// Copyright (c) Microsoft Corporation. All rights reserved.
// AggregateMessage.cs

using System;
using System.Collections.Generic;

namespace AutoGen.Core;

public class AggregateMessage<TMessage1, TMessage2> : IMessage
    where TMessage1 : IMessage
    where TMessage2 : IMessage
{
    public AggregateMessage(TMessage1 message1, TMessage2 message2, string? from = null)
    {
        this.From = from;
        this.Message1 = message1;
        this.Message2 = message2;
        this.Validate();
    }

    public TMessage1 Message1 { get; }

    public TMessage2 Message2 { get; }

    public string? From { get; set; }

    private void Validate()
    {
        var messages = new List<IMessage> { this.Message1, this.Message2 };
        // the from property of all messages should be the same with the from property of the aggregate message

        foreach (var message in messages)
        {
            if (message.From != this.From)
            {
                throw new ArgumentException($"The from property of the message {message} is different from the from property of the aggregate message {this}");
            }
        }
    }

    public override string ToString()
    {
        var stringBuilder = new System.Text.StringBuilder();
        var messages = new List<IMessage> { this.Message1, this.Message2 };
        stringBuilder.Append($"AggregateMessage({this.From})");
        foreach (var message in messages)
        {
            stringBuilder.Append($"\n\t{message}");
        }

        return stringBuilder.ToString();
    }
}
