using System;

/// <summary>
/// Add support for consuming openai-like API from LM Studio
/// </summary>
public class OllamaConfig : ILLMConfig
{
    public OllamaConfig(string host, int port, int version = 1)
    {
        this.Host = host;
        this.Port = port;
        this.Version = version;
    }

    public string Host { get; }

    public int Port { get; }

    public int Version { get; }

    public Uri Uri => new Uri($"http://{Host}:{Port}/v{Version}");
}
