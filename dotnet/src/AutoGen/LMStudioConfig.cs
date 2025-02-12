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
    public LMStudioConfig(string host, int port, string modelName)
    {
        this.Host = host;
        this.Port = port;
        this.Uri = new Uri($"http://{host}:{port}/v1");
        if (modelName == null)
        {
            throw new ArgumentNullException("modelName is a required property for LMStudioConfig and cannot be null");
        }
        this.ModelName = modelName;
    }

    public LMStudioConfig(Uri uri, string modelName)
    {
        this.Uri = uri;
        this.Host = uri.Host;
        this.Port = uri.Port;
        if (modelName == null)
        {
            throw new ArgumentNullException("modelName is a required property for LMStudioConfig and cannot be null");
        }
        this.ModelName = modelName;
    }

    public string Host { get; }

    public int Port { get; }

    public Uri Uri { get; }

    public string ModelName { get; }

    internal ChatClient CreateChatClient()
    {
        var client = new OpenAIClient(new ApiKeyCredential("api-key"), new OpenAIClientOptions
        {
            Endpoint = this.Uri,
        });

        return client.GetChatClient(this.ModelName);
    }
}
