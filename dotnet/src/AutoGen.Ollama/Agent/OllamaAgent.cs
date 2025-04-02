// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaAgent.cs

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;

namespace AutoGen.Ollama;

/// <summary>
/// An agent that can interact with ollama models.
/// </summary>
public class OllamaAgent : IStreamingAgent
{
    private readonly HttpClient _httpClient;
    private readonly string _modelName;
    private readonly string _systemMessage;
    private readonly OllamaReplyOptions? _replyOptions;

    public OllamaAgent(HttpClient httpClient, string name, string modelName,
        string systemMessage = "You are a helpful AI assistant",
        OllamaReplyOptions? replyOptions = null)
    {
        Name = name;
        _httpClient = httpClient;
        _modelName = modelName;
        _systemMessage = systemMessage;
        _replyOptions = replyOptions;
    }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellation = default)
    {
        ChatRequest request = await BuildChatRequest(messages, options);
        request.Stream = false;
        var httpRequest = BuildRequest(request);
        using (HttpResponseMessage? response = await _httpClient.SendAsync(httpRequest, HttpCompletionOption.ResponseContentRead, cancellation))
        {
            response.EnsureSuccessStatusCode();
            Stream? streamResponse = await response.Content.ReadAsStreamAsync();
            ChatResponse chatResponse = await JsonSerializer.DeserializeAsync<ChatResponse>(streamResponse, cancellationToken: cancellation)
                                                           ?? throw new Exception("Failed to deserialize response");
            var output = new MessageEnvelope<ChatResponse>(chatResponse, from: Name);
            return output;
        }
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ChatRequest request = await BuildChatRequest(messages, options);
        request.Stream = true;
        HttpRequestMessage message = BuildRequest(request);
        using (HttpResponseMessage? response = await _httpClient.SendAsync(message, HttpCompletionOption.ResponseHeadersRead, cancellationToken))
        {
            response.EnsureSuccessStatusCode();
            using Stream? stream = await response.Content.ReadAsStreamAsync().ConfigureAwait(false);
            using var reader = new StreamReader(stream);

            while (!reader.EndOfStream && !cancellationToken.IsCancellationRequested)
            {
                string? line = await reader.ReadLineAsync();
                if (string.IsNullOrWhiteSpace(line))
                {
                    continue;
                }

                ChatResponseUpdate? update = JsonSerializer.Deserialize<ChatResponseUpdate>(line);
                if (update is { Done: false })
                {
                    yield return new MessageEnvelope<ChatResponseUpdate>(update, from: Name);
                }
                else
                {
                    var finalUpdate = JsonSerializer.Deserialize<ChatResponse>(line) ?? throw new Exception("Failed to deserialize response");

                    yield return new MessageEnvelope<ChatResponse>(finalUpdate, from: Name);
                }
            }
        }
    }

    public string Name { get; }

    private async Task<ChatRequest> BuildChatRequest(IEnumerable<IMessage> messages, GenerateReplyOptions? options)
    {
        var request = new ChatRequest
        {
            Model = _modelName,
            Messages = await BuildChatHistory(messages)
        };

        if (options is OllamaReplyOptions replyOptions)
        {
            BuildChatRequestOptions(replyOptions, request);
            return request;
        }

        if (_replyOptions != null)
        {
            BuildChatRequestOptions(_replyOptions, request);
            return request;
        }
        return request;
    }
    private void BuildChatRequestOptions(OllamaReplyOptions replyOptions, ChatRequest request)
    {
        request.Format = replyOptions.Format == FormatType.Json ? OllamaConsts.JsonFormatType : null;
        request.Template = replyOptions.Template;
        request.KeepAlive = replyOptions.KeepAlive;

        if (replyOptions.Temperature != null
            || replyOptions.MaxToken != null
            || replyOptions.StopSequence != null
            || replyOptions.Seed != null
            || replyOptions.MiroStat != null
            || replyOptions.MiroStatEta != null
            || replyOptions.MiroStatTau != null
            || replyOptions.NumCtx != null
            || replyOptions.NumGqa != null
            || replyOptions.NumGpu != null
            || replyOptions.NumThread != null
            || replyOptions.RepeatLastN != null
            || replyOptions.RepeatPenalty != null
            || replyOptions.TopK != null
            || replyOptions.TopP != null
            || replyOptions.TfsZ != null)
        {
            request.Options = new ModelReplyOptions
            {
                Temperature = replyOptions.Temperature,
                NumPredict = replyOptions.MaxToken,
                Stop = replyOptions.StopSequence?[0],
                Seed = replyOptions.Seed,
                MiroStat = replyOptions.MiroStat,
                MiroStatEta = replyOptions.MiroStatEta,
                MiroStatTau = replyOptions.MiroStatTau,
                NumCtx = replyOptions.NumCtx,
                NumGqa = replyOptions.NumGqa,
                NumGpu = replyOptions.NumGpu,
                NumThread = replyOptions.NumThread,
                RepeatLastN = replyOptions.RepeatLastN,
                RepeatPenalty = replyOptions.RepeatPenalty,
                TopK = replyOptions.TopK,
                TopP = replyOptions.TopP,
                TfsZ = replyOptions.TfsZ
            };
        }
    }
    private async Task<List<Message>> BuildChatHistory(IEnumerable<IMessage> messages)
    {
        var history = messages.Select(m => m switch
        {
            IMessage<Message> chatMessage => chatMessage.Content,
            _ => throw new ArgumentException("Invalid message type")
        });

        // if there's no system message in the history, add one to the beginning
        if (!history.Any(m => m.Role == "system"))
        {
            history = new[] { new Message() { Role = "system", Value = _systemMessage } }.Concat(history);
        }

        return history.ToList();
    }

    private static HttpRequestMessage BuildRequest(ChatRequest request)
    {
        string serialized = JsonSerializer.Serialize(request);
        return new HttpRequestMessage(HttpMethod.Post, OllamaConsts.ChatCompletionEndpoint)
        {
            Content = new StringContent(serialized, Encoding.UTF8, OllamaConsts.JsonMediaType)
        };
    }
}
