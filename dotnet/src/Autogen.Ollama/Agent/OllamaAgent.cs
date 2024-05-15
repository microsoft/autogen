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

namespace Autogen.Ollama;

/// <summary>
/// An agent that can interact with ollama models.
/// </summary>
public class OllamaAgent : IStreamingAgent
{
    private readonly HttpClient _httpClient;
    public string Name { get; }
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
        using (HttpResponseMessage? response = await _httpClient
                   .SendAsync(BuildRequestMessage(request), HttpCompletionOption.ResponseContentRead, cancellation))
        {
            response.EnsureSuccessStatusCode();
            Stream? streamResponse = await response.Content.ReadAsStreamAsync();
            ChatResponse chatResponse = await JsonSerializer.DeserializeAsync<ChatResponse>(streamResponse, cancellationToken: cancellation)
                                                           ?? throw new Exception("Failed to deserialize response");
            var output = new MessageEnvelope<ChatResponse>(chatResponse, from: Name);
            return output;
        }
    }
    public async IAsyncEnumerable<IStreamingMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ChatRequest request = await BuildChatRequest(messages, options);
        request.Stream = true;
        HttpRequestMessage message = BuildRequestMessage(request);
        using (HttpResponseMessage? response = await _httpClient.SendAsync(message, HttpCompletionOption.ResponseHeadersRead, cancellationToken))
        {
            response.EnsureSuccessStatusCode();
            using Stream? stream = await response.Content.ReadAsStreamAsync().ConfigureAwait(false);
            using var reader = new StreamReader(stream);

            while (!reader.EndOfStream && !cancellationToken.IsCancellationRequested)
            {
                string? line = await reader.ReadLineAsync();
                if (string.IsNullOrWhiteSpace(line)) continue;

                ChatResponseUpdate? update = JsonSerializer.Deserialize<ChatResponseUpdate>(line);
                if (update != null)
                {
                    yield return new MessageEnvelope<ChatResponseUpdate>(update, from: Name);
                }

                if (update is { Done: false }) continue;

                ChatResponse? chatMessage = JsonSerializer.Deserialize<ChatResponse>(line);
                if (chatMessage == null) continue;
                yield return new MessageEnvelope<ChatResponse>(chatMessage, from: Name);
            }
        }
    }
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
                    string base64Image = await ImageUrlToBase64(im.Url!);
                    item = new Message { Role = im.Role.ToString(), Images = [base64Image] };
                    break;
                case MultiModalMessage mm:
                    var textsGroupedByRole = mm.Content.OfType<TextMessage>().GroupBy(tm => tm.Role)
                        .ToDictionary(g => g.Key, g => string.Join(Environment.NewLine, g.Select(tm => tm.Content)));

                    string content = string.Join($"{Environment.NewLine}", textsGroupedByRole
                        .Select(g => $"{g.Key}{Environment.NewLine}:{g.Value}"));

                    IEnumerable<Task<string>> imagesConversionTasks = mm.Content
                        .OfType<ImageMessage>()
                        .Select(async im => await ImageUrlToBase64(im.Url!));

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
    private static HttpRequestMessage BuildRequestMessage(ChatRequest request)
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
