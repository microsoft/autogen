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

    public ImageMessage(Role role, BinaryData data, string? from = null)
    {
        if (data.IsEmpty)
        {
            throw new ArgumentException("Data cannot be empty", nameof(data));
        }

        if (string.IsNullOrWhiteSpace(data.MediaType))
        {
            throw new ArgumentException("MediaType is needed for DataUri Images", nameof(data));
        }

        this.Role = role;
        this.From = from;
        this.Data = data;
    }

    public Role Role { get; set; }

    public string? Url { get; set; }

    public string? From { get; set; }

    public BinaryData? Data { get; set; }

    public string BuildDataUri()
    {
        if (this.Data is null)
        {
            throw new NullReferenceException($"{nameof(Data)}");
        }

        return $"data:{this.Data.MediaType};base64,{Convert.ToBase64String(this.Data.ToArray())}";
    }

    public override string ToString()
    {
        return $"ImageMessage({this.Role}, {(this.Data != null ? BuildDataUri() : this.Url) ?? string.Empty}, {this.From})";
    }
}
