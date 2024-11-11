// Copyright (c) Microsoft Corporation. All rights reserved.
// LMStudioConfig.cs

using System;
using System.ClientModel;
using OpenAI;
using OpenAI.Chat;

namespace AutoGen;

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

    internal ChatClient CreateChatClient()
    {
        var client = new OpenAIClient(new ApiKeyCredential("api-key"), new OpenAIClientOptions
        {
            Endpoint = this.Uri,
        });

        // model name doesn't matter for LM Studio

        return client.GetChatClient("model-name");
    }
}
