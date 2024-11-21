// Copyright (c) Microsoft Corporation. All rights reserved.
// ImageMessage.cs

using System;
using System.Text.RegularExpressions;

namespace AutoGen.Core;

public class ImageMessage : IMessage
{
    private static readonly Regex s_DataUriRegex = new Regex(@"^data:(?<mediatype>[^;]+);base64,(?<data>.*)$", RegexOptions.Compiled);

    /// <summary>
    /// Create an ImageMessage from a url.
    /// The url can be a regular url or a data uri.
    /// If the url is a data uri, the scheme must be "data" and the format must be data:[<mediatype>][;base64],<data>
    /// </summary>
    public ImageMessage(Role role, string url, string? from = null, string? mimeType = null)
    {
        this.Role = role;
        this.From = from;

        // url might be a data uri or a regular url
        if (url.StartsWith("data:", StringComparison.OrdinalIgnoreCase))
        {
            // the url must be in the format of data:[<mediatype>][;base64],<data>
            var match = s_DataUriRegex.Match(url);

            if (!match.Success)
            {
                throw new ArgumentException("Invalid DataUri format, expected data:[<mediatype>][;base64],<data>", nameof(url));
            }

            this.Data = new BinaryData(Convert.FromBase64String(match.Groups["data"].Value), match.Groups["mediatype"].Value);

            this.MimeType = match.Groups["mediatype"].Value;
        }
        else
        {
            this.Url = url;
            // try infer mimeType from uri extension if not provided
            if (mimeType is null)
            {
                mimeType = url switch
                {
                    _ when url.EndsWith(".png", StringComparison.OrdinalIgnoreCase) => "image/png",
                    _ when url.EndsWith(".jpg", StringComparison.OrdinalIgnoreCase) => "image/jpeg",
                    _ when url.EndsWith(".jpeg", StringComparison.OrdinalIgnoreCase) => "image/jpeg",
                    _ when url.EndsWith(".gif", StringComparison.OrdinalIgnoreCase) => "image/gif",
                    _ when url.EndsWith(".bmp", StringComparison.OrdinalIgnoreCase) => "image/bmp",
                    _ when url.EndsWith(".webp", StringComparison.OrdinalIgnoreCase) => "image/webp",
                    _ when url.EndsWith(".svg", StringComparison.OrdinalIgnoreCase) => "image/svg+xml",
                    _ => throw new ArgumentException("MimeType is required for ImageMessage", nameof(mimeType))
                };
            }

            this.MimeType = mimeType;
        }
    }

    public ImageMessage(Role role, Uri uri, string? from = null, string? mimeType = null)
        : this(role, uri.ToString(), from, mimeType)
    {
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
