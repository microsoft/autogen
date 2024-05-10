// Copyright (c) Microsoft Corporation. All rights reserved.
// LMStudioConfig.cs

using System;

/// <summary>
/// Add support for consuming openai-like API from LM Studio
/// </summary>
public class LMStudioConfig : ILLMConfig
{
    public LMStudioConfig(string host, int port, int version = 1)
    {
        this.Host = host;
        this.Port = port;
        this.Version = version;
        this.Uri = new Uri($"http://{host}:{port}/v{version}");
    }

    public LMStudioConfig(Uri uri)
    {
        this.Uri = uri;
        this.Host = uri.Host;
        this.Port = uri.Port;
        this.Version = int.Parse(uri.Segments[1].TrimStart('v'));
    }

    public string Host { get; }

    public int Port { get; }

    public int Version { get; }

    public Uri Uri { get; }
}
