// Copyright (c) Microsoft Corporation. All rights reserved.
// ImageMessage.cs

using System;

namespace AutoGen.Core;

public class ImageMessage : IMessage
{
    public ImageMessage(Role role, string url, string? from = null)
    {
        this.Role = role;
        this.From = from;
        this.Url = url;
    }

    public ImageMessage(Role role, Uri uri, string? from = null)
    {
        this.Role = role;
        this.From = from;
        this.Url = uri.ToString();
    }

    public Role Role { get; set; }

    public string Url { get; set; }

    public string? From { get; set; }

    public override string ToString()
    {
        return $"ImageMessage({this.Role}, {this.Url}, {this.From})";
    }
}
