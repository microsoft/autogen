// Copyright (c) Microsoft Corporation. All rights reserved.
// LMStudioConfig.cs

using System;

/// <summary>
/// Add support for consuming openai-like API from LM Studio
/// </summary>
public class LMStudioConfig : ILLMConfig
{
    public LMStudioConfig(string host, int port)
    {
        this.Host = host;
        this.Port = port;
        this.Uri = new Uri($"http://{host}:{port}");
    }

    public LMStudioConfig(Uri uri)
    {
        this.Uri = uri;
        this.Host = uri.Host;
        this.Port = uri.Port;
    }

    public string Host { get; }

    public int Port { get; }

    public Uri Uri { get; }
}
