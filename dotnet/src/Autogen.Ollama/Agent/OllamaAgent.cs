// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaAgent.cs

using System.Collections.Generic;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;

namespace Autogen.Ollama;

public class OllamaAgent : IStreamingAgent
{
    public string Name { get; }
    private readonly IStreamingAgent _innerAgent;
    public OllamaAgent(
        HttpClient httpClient,
        string name,
        string modelName,
        string systemMessage = "You are a helpful AI assistant",
        OllamaReplyOptions? replyOptions = null)
    {
        _innerAgent = new OllamaClientAgent(httpClient, name, modelName, systemMessage, replyOptions);
        Name = _innerAgent.Name;
    }

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null,
        CancellationToken cancellation = default)
    {
        var connector = new OllamaMessageConnector();
        MiddlewareAgent<IStreamingAgent> agent = _innerAgent.RegisterMiddleware(connector);
        return await agent.GenerateReplyAsync(messages, options, cancellation);
    }


    public async Task<IAsyncEnumerable<IStreamingMessage>> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var connector = new OllamaMessageConnector();
        MiddlewareStreamingAgent<IStreamingAgent> agent = _innerAgent.RegisterStreamingMiddleware(connector);
        return await agent.GenerateStreamingReplyAsync(messages, options, cancellationToken);
    }
}
