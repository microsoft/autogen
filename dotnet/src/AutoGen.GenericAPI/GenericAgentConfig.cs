// Copyright (c) Microsoft Corporation. All rights reserved.
// GenericAgentConfig.cs

using System;
using AutoGen;

/// <summary>
///     Add support for consuming openai-like API from different LLM providers like Mistral, Groq and OpenRouter
///     HttpScheme is used to specify the protocol to use for the API
/// </summary>
public class GenericAgentConfig : ILLMConfig
{
    public GenericAgentConfig(string apiToken, HttpScheme httpScheme, string host, string modelName, int port = 0,
        int version = 1)
    {
        ApiToken = apiToken;
        HttpScheme = httpScheme;
        Host = host;
        ModelName = modelName;
        Port = port;
        Version = version;
    }

    public GenericAgentConfig(string apiToken, string host, string modelName, int port = 0, int version = 1)
    {
        ApiToken = apiToken;
        HttpScheme = HttpScheme.Https;
        Host = host;
        ModelName = modelName;
        Port = port;
        Version = version;
    }

    //used for LMStudio
    public GenericAgentConfig(HttpScheme httpScheme, string host, int port = 0, int version = 1)
    {
        HttpScheme = httpScheme;
        Host = host;
        Port = port;
        Version = version;
        ModelName = "llm";
    }

    public string ApiToken { get; } = string.Empty;
    public HttpScheme HttpScheme { get; }
    public string Host { get; }
    public string ModelName { get; }
    public int Port { get; }
    public int Version { get; }

    public Uri Uri
    {
        get
        {
            if (Port != 0)
            {
                return new Uri($"{HttpScheme.ToString()}://{Host}:{Port}/v{Version}");
            }

            return new Uri($"{HttpScheme}://{Host}/v{Version}");
        }
    }
}
