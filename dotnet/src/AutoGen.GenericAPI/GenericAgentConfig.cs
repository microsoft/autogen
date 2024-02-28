// Copyright (c) Microsoft Corporation. All rights reserved.
// GenericAgentConfig.cs

using System;
using AutoGen;

/// <summary>
///     Add support for consuming openai-like API from LM Studio
/// </summary>
public class GenericAgentConfig : ILLMConfig
{
    public GenericAgentConfig(string apiToken,string host, int port=0, int version = 1)
    {
        ApiToken = apiToken;
        Host = host;
        Port = port;
        Version = version;
    }

    public string ApiToken { get; }
    public string Host { get; }
    public int Port { get; }

    public int Version { get; }

    public Uri Uri
    {
        get
        {
            if (Port > 0)
            {
                return new Uri($"https://{Host}:{Port}/v{Version}");
            }

            return new Uri($"https://{Host}/v{Version}");
        }
    }
}
