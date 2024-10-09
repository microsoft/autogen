// Copyright (c) Microsoft Corporation. All rights reserved.
// ImageMessage.cs

using System;

namespace AutoGen.Core;

public class ImageMessage : IMessage
{
    public ImageMessage(Role role, string url, string? from = null, string? mimeType = null)
        : this(role, new Uri(url), from, mimeType)
    {
    }

    public ImageMessage(Role role, Uri uri, string? from = null, string? mimeType = null)
    {
        this.Role = role;
        this.From = from;
        this.Url = uri.ToString();

        // try infer mimeType from uri extension if not provided
        if (mimeType is null)
        {
            mimeType = uri switch
            {
                _ when uri.AbsoluteUri.EndsWith(".png", StringComparison.OrdinalIgnoreCase) => "image/png",
                _ when uri.AbsoluteUri.EndsWith(".jpg", StringComparison.OrdinalIgnoreCase) => "image/jpeg",
                _ when uri.AbsoluteUri.EndsWith(".jpeg", StringComparison.OrdinalIgnoreCase) => "image/jpeg",
                _ when uri.AbsoluteUri.EndsWith(".gif", StringComparison.OrdinalIgnoreCase) => "image/gif",
                _ when uri.AbsoluteUri.EndsWith(".bmp", StringComparison.OrdinalIgnoreCase) => "image/bmp",
                _ when uri.AbsoluteUri.EndsWith(".webp", StringComparison.OrdinalIgnoreCase) => "image/webp",
                _ when uri.AbsoluteUri.EndsWith(".svg", StringComparison.OrdinalIgnoreCase) => "image/svg+xml",
                _ => throw new ArgumentException("MimeType is required for ImageMessage", nameof(mimeType))
            };
        }

        this.MimeType = mimeType;
    }

    public ImageMessage(Role role, BinaryData data, string? from = null)
    {
        if (data.IsEmpty)
        {
            throw new ArgumentException("Data cannot be empty", nameof(data));
        }

        if (data.MediaType is null)
        {
            throw new ArgumentException("MediaType is needed for DataUri Images", nameof(data));
        }

        this.Role = role;
        this.From = from;
        this.Data = data;
        this.MimeType = data.MediaType;
    }

    public Role Role { get; }

    public string? Url { get; }

    public string? From { get; set; }

    public BinaryData? Data { get; }

    public string MimeType { get; }

    public string BuildDataUri()
    {
        if (this.Data is null)
        {
            throw new ArgumentNullException($"{nameof(Data)}");
        }

        return $"data:{this.MimeType};base64,{Convert.ToBase64String(this.Data.ToArray())}";
    }

    public override string ToString()
    {
        return $"ImageMessage({this.Role}, {(this.Data != null ? BuildDataUri() : this.Url) ?? string.Empty}, {this.From})";
    }
}
