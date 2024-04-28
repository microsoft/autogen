// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaClientAgent.cs

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;

namespace Autogen.Ollama;

/// <summary>
/// An agent that can interact with ollama models.
/// </summary>
public class OllamaClientAgent : IStreamingAgent
{
    private readonly HttpClient _httpClient;
    public string Name { get; }
    private readonly string _modelName;
    private readonly string _systemMessage;
    private readonly OllamaReplyOptions? _replyOptions;

    public OllamaClientAgent(HttpClient httpClient, string name, string modelName,
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
        ChatMessageRequest request = await BuildChatRequest(messages, options);
        request.Stream = false;
        using (HttpResponseMessage? response = await _httpClient
                   .SendAsync(BuildRequestMessage(request), HttpCompletionOption.ResponseContentRead, cancellation))
        {
            response.EnsureSuccessStatusCode();
            CompleteChatMessage reply = await response.Content
                .ReadFromJsonAsync<CompleteChatMessage>(cancellationToken: cancellation)
                                    ?? throw new InvalidOperationException();
            return new MessageEnvelope<CompleteChatMessage>(reply, from: Name);
        }
    }

    public async Task<IAsyncEnumerable<IStreamingMessage>> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellation = default)
    {
        ChatMessageRequest request = await BuildChatRequest(messages, options);
        request.Stream = true;
        return StreamMessagesAsync(request, cancellation);
    }
    private async IAsyncEnumerable<IStreamingMessage> StreamMessagesAsync(
        ChatMessageRequest request, [EnumeratorCancellation] CancellationToken cancellation)
    {
        HttpRequestMessage message = BuildRequestMessage(request);
        using (HttpResponseMessage? response = await _httpClient.SendAsync(message, HttpCompletionOption.ResponseHeadersRead, cancellation))
        {
            response.EnsureSuccessStatusCode();
            using Stream? stream = await response.Content.ReadAsStreamAsync().ConfigureAwait(false);
            using var reader = new StreamReader(stream);

            while (!reader.EndOfStream && !cancellation.IsCancellationRequested)
            {
                string? line = await reader.ReadLineAsync();
                if (string.IsNullOrWhiteSpace(line)) continue;

                ChatMessage? update = JsonSerializer.Deserialize<ChatMessage>(line);
                if (update != null)
                {
                    yield return new MessageEnvelope<ChatMessage>(update, from: Name);
                }

                if (update is { Done: false }) continue;

                CompleteChatMessage? chatMessage = JsonSerializer.Deserialize<CompleteChatMessage>(line);
                if (chatMessage == null) continue;
                yield return new MessageEnvelope<CompleteChatMessage>(chatMessage, from: Name);
            }
        }
    }
    private async Task<ChatMessageRequest> BuildChatRequest(IEnumerable<IMessage> messages, GenerateReplyOptions? options)
    {
        var request = new ChatMessageRequest
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
    private void BuildChatRequestOptions(OllamaReplyOptions replyOptions, ChatMessageRequest request)
    {
        request.Format = replyOptions.Format == FormatType.Json ? OllamaConsts.JsonFormatType : null;
        request.Template = replyOptions.Template;
        request.KeepAlive = replyOptions.KeepAlive;
        request.Options.Temperature = replyOptions.Temperature;
        request.Options.NumPredict = replyOptions.MaxToken;
        request.Options.Stop = replyOptions.StopSequence?[0];
        request.Options.Seed = replyOptions.Seed;
        request.Options.MiroStat = replyOptions.MiroStat;
        request.Options.MiroStatEta = replyOptions.MiroStatEta;
        request.Options.MiroStatTau = replyOptions.MiroStatTau;
        request.Options.NumCtx = replyOptions.NumCtx;
        request.Options.NumGqa = replyOptions.NumGqa;
        request.Options.NumGpu = replyOptions.NumGpu;
        request.Options.NumThread = replyOptions.NumThread;
        request.Options.RepeatLastN = replyOptions.RepeatLastN;
        request.Options.RepeatPenalty = replyOptions.RepeatPenalty;
        request.Options.TopK = replyOptions.TopK;
        request.Options.TopP = replyOptions.TopP;
        request.Options.TfsZ = replyOptions.TfsZ;
    }
    private async Task<List<Message>> BuildChatHistory(IEnumerable<IMessage> messages)
    {
        if (!messages.Any(m => m.IsSystemMessage()))
        {
            var systemMessage = new TextMessage(Role.System, _systemMessage, from: Name);
            messages = new[] { systemMessage }.Concat(messages);
        }

        var collection = new List<Message>();
        foreach (IMessage? message in messages)
        {
            Message item;
            switch (message)
            {
                case TextMessage tm:
                    item = new Message { Role = tm.Role.ToString(), Value = tm.Content };
                    break;
                case ImageMessage im:
                    string base64Image = await ImageUrlToBase64(im.Url);
                    item = new Message { Role = im.Role.ToString(), Images = [base64Image] };
                    break;
                case MultiModalMessage mm:
                    var textsGroupedByRole = mm.Content.OfType<TextMessage>().GroupBy(tm => tm.Role)
                        .ToDictionary(g => g.Key, g => string.Join(Environment.NewLine, g.Select(tm => tm.Content)));

                    string content = string.Join($"{Environment.NewLine}", textsGroupedByRole
                        .Select(g => $"{g.Key}{Environment.NewLine}:{g.Value}"));

                    IEnumerable<Task<string>> imagesConversionTasks = mm.Content
                        .OfType<ImageMessage>()
                        .Select(async im => await ImageUrlToBase64(im.Url));

                    string[]? imagesBase64 = await Task.WhenAll(imagesConversionTasks);
                    item = new Message { Role = mm.Role.ToString(), Value = content, Images = imagesBase64 };
                    break;
                default:
                    throw new NotSupportedException();
            }

            collection.Add(item);
        }

        return collection;
    }

    private static HttpRequestMessage BuildRequestMessage(ChatMessageRequest request)
    {
        string serialized = JsonSerializer.Serialize(request);
        return new HttpRequestMessage(HttpMethod.Post, OllamaConsts.ChatCompletionEndpoint)
        {
            Content = new StringContent(serialized, Encoding.UTF8, OllamaConsts.JsonMediaType)
        };
    }
    private async Task<string> ImageUrlToBase64(string imageUrl)
    {
        if (string.IsNullOrWhiteSpace(imageUrl))
        {
            throw new ArgumentException("required parameter", nameof(imageUrl));
        }
        byte[] imageBytes = await _httpClient.GetByteArrayAsync(imageUrl);
        return imageBytes != null
            ? Convert.ToBase64String(imageBytes)
            : throw new InvalidOperationException("no image byte array");
    }
}
