// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicChatCompletionClient.cs

using System.Runtime.CompilerServices;
using AutoGen.Anthropic.DTO;
using Microsoft.Extensions.AI;
using MEAI = Microsoft.Extensions.AI;
using DTO = AutoGen.Anthropic.DTO;

using AutoGen.Anthropic;

#if NET8_0_OR_GREATER
using System.Diagnostics.CodeAnalysis;
#endif

namespace Microsoft.AutoGen.Extensions.Anthropic;

public static class AnthropicChatCompletionDefaults
{
    //public const string DefaultSystemMessage = "You are a helpful AI assistant";
    public const decimal DefaultTemperature = 0.7m;
    public const int DefaultMaxTokens = 1024;
}

public sealed class AnthropicChatCompletionClient : IChatClient, IDisposable
{
    private AnthropicClient? _anthropicClient;
    private string _modelId;

    public AnthropicChatCompletionClient(HttpClient httpClient, string modelId, string baseUrl, string apiKey)
        : this(new AnthropicClient(httpClient, baseUrl, apiKey), modelId)
    {
    }

    public AnthropicChatCompletionClient(
#if NET8_0_OR_GREATER // TODO: Should this be lower?
        [NotNull]
#endif
    AnthropicClient client, string modelId)
    {
        if (client == null)
        {
            throw new ArgumentNullException(nameof(client));
        }

        _anthropicClient = client;
        _modelId = modelId;

        if (!Uri.TryCreate(client.BaseUrl, UriKind.Absolute, out Uri? uri))
        {
            // technically we should never be able to get this far, in this case
            throw new ArgumentException($"Invalid base URL in provided client: {client.BaseUrl}", nameof(client));
        }

        this.Metadata = new ChatClientMetadata("Anthropic", uri, modelId);
    }

    public ChatClientMetadata Metadata { get; private set; }

    private DTO.ChatMessage Translate(MEAI.ChatMessage message, List<SystemMessage>? systemMessagesSink = null)
    {
        if (message.Role == ChatRole.System && systemMessagesSink != null)
        {
            if (message.Contents.Count != 1 || message.Text == null)
            {
                throw new Exception($"Invalid SystemMessage: May only contain a single Text AIContent. Actual: {
                    String.Join(",", from contentObject in message.Contents select contentObject.GetType())
                }");
            }

            systemMessagesSink.Add(SystemMessage.CreateSystemMessage(message.Text));
        }

        List<ContentBase> contents = new(from rawContent in message.Contents select (DTO.ContentBase)rawContent);
        return new DTO.ChatMessage(message.Role.ToString().ToLowerInvariant(), contents);
    }

    private ChatCompletionRequest CreateRequest(IList<MEAI.ChatMessage> chatMessages, ChatOptions? options, bool requestStream)
    {
        ToolChoice? toolChoice = null;
        ChatToolMode? mode = options?.ToolMode;

        if (mode is AutoChatToolMode)
        {
            toolChoice = ToolChoice.Auto;
        }
        else if (mode is RequiredChatToolMode requiredToolMode)
        {
            if (requiredToolMode.RequiredFunctionName == null)
            {
                toolChoice = ToolChoice.Any;
            }
            else
            {
                toolChoice = ToolChoice.ToolUse(requiredToolMode.RequiredFunctionName!);
            }
        }

        List<SystemMessage> systemMessages = new List<SystemMessage>();
        List<DTO.ChatMessage> translatedMessages = new();

        foreach (MEAI.ChatMessage message in chatMessages)
        {
            if (message.Role == ChatRole.System)
            {
                Translate(message, systemMessages);

                // TODO: Should the system messages be included in the translatedMessages list?
            }
            else
            {
                translatedMessages.Add(Translate(message));
            }
        }

        return new ChatCompletionRequest
        {
            Model = _modelId,

            // TODO: We should consider coming up with a reasonable default for MaxTokens, since the MAAi APIs do not require
            // it, while our wrapper for the Anthropic API does.
            MaxTokens = options?.MaxOutputTokens ?? throw new ArgumentException("Must specify number of tokens in request for Anthropic", nameof(options)),
            StopSequences = options?.StopSequences?.ToArray(),
            Stream = requestStream,
            Temperature = (decimal?)options?.Temperature, // TODO: why `decimal`?!
            ToolChoice = toolChoice,
            Tools = (from abstractTool in options?.Tools
                     where abstractTool is AIFunction
                     select (Tool)(AIFunction)abstractTool).ToList(),
            TopK = options?.TopK,
            TopP = (decimal?)options?.TopP,
            SystemMessage = systemMessages.ToArray(),
            Messages = translatedMessages,

            // TODO: put these somewhere? .Metadata?
            //ModelId = _modelId,
            //Options = options
        };
    }

    private sealed class ChatCompletionAccumulator
    {
        public string? CompletionId { get; set; }
        public string? ModelId { get; set; }
        public MEAI.ChatRole? StreamingRole { get; set; }
        public MEAI.ChatFinishReason? FinishReason { get; set; }
        // public DateTimeOffset CreatedAt { get; set; }

        public ChatCompletionAccumulator() { }

        public List<AIContent>? AccumulateAndExtractContent(ChatCompletionResponse response)
        {
            this.CompletionId ??= response.Id;
            this.ModelId ??= response.Model;

            this.FinishReason ??= response.StopReason switch
            {
                "end_turn" => MEAI.ChatFinishReason.Stop,
                "stop_sequence" => MEAI.ChatFinishReason.Stop,
                "tool_use" => MEAI.ChatFinishReason.ToolCalls,
                "max_tokens" => MEAI.ChatFinishReason.Length,
                _ => null
            };

            this.StreamingRole ??= response.Role switch
            {
                "assistant" => MEAI.ChatRole.Assistant,
                //"user" => MEAI.ChatRole.User,
                //null => null,
                _ => throw new InvalidOperationException("Anthropic API is defined to only reply with 'assistant'.")
            };

            if (response.Content == null)
            {
                return null;
            }

            return new(from rawContent in response.Content select (MEAI.AIContent)rawContent);
        }

    }

    private MEAI.ChatCompletion TranslateCompletion(ChatCompletionResponse response)
    {
        ChatCompletionAccumulator accumulator = new ChatCompletionAccumulator();
        List<AIContent>? messageContents = accumulator.AccumulateAndExtractContent(response);

        // According to the Anthropic API docs, the response will contain a single "option" in the MEAI
        // parlance, but may contain multiple message? (I suspect for the purposes of tool use)
        if (messageContents == null)
        {
            throw new ArgumentNullException(nameof(response.Content));
        }
        else if (messageContents.Count == 0)
        {
            throw new ArgumentException("Response did not contain any content", nameof(response));
        }

        MEAI.ChatMessage message = new(ChatRole.Assistant, messageContents);

        return new MEAI.ChatCompletion(message)
        {
            CompletionId = accumulator.CompletionId,
            ModelId = accumulator.ModelId,
            //CreatedAt = TODO:
            FinishReason = accumulator.FinishReason,
            // Usage = TODO: extract this from the DTO
            RawRepresentation = response
            // WIP
        };
    }

    private MEAI.StreamingChatCompletionUpdate TranslateStreamingUpdate(ChatCompletionAccumulator accumulator, ChatCompletionResponse response)
    {
        List<AIContent>? messageContents = accumulator.AccumulateAndExtractContent(response);

        // messageContents will be non-null only on the final "tool_call" stop message update, which will contain
        // all of the accumulated ToolUseContent objects.
        if (messageContents == null && response.Delta != null && response.Delta.Type == "text_delta")
        {
            messageContents = new List<AIContent> { new MEAI.TextContent(response.Delta.Text) };
        }

        return new MEAI.StreamingChatCompletionUpdate
        {
            Role = accumulator.StreamingRole,
            CompletionId = accumulator.CompletionId,
            ModelId = accumulator.ModelId,
            //CreatedAt = TODO:
            FinishReason = accumulator.FinishReason,
            //ChoiceIndex = 0,
            Contents = messageContents,
            RawRepresentation = response
        };
    }

    public async Task<MEAI.ChatCompletion> CompleteAsync(IList<Microsoft.Extensions.AI.ChatMessage> chatMessages, ChatOptions? options = null, CancellationToken cancellationToken = default)
    {
        ChatCompletionRequest request = CreateRequest(chatMessages, options, requestStream: false);
        ChatCompletionResponse response = await this.EnsureClient().CreateChatCompletionsAsync(request, cancellationToken);

        return TranslateCompletion(response);
    }

    private AnthropicClient EnsureClient()
    {
        return this._anthropicClient ?? throw new ObjectDisposedException(nameof(AnthropicChatCompletionClient));
    }

    public async IAsyncEnumerable<MEAI.StreamingChatCompletionUpdate> CompleteStreamingAsync(IList<Microsoft.Extensions.AI.ChatMessage> chatMessages, ChatOptions? options = null, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ChatCompletionRequest request = CreateRequest(chatMessages, options, requestStream: true);
        IAsyncEnumerable<ChatCompletionResponse> responseStream = this.EnsureClient().StreamingChatCompletionsAsync(request, cancellationToken);

        // TODO: There is likely a better way to do this
        ChatCompletionAccumulator accumulator = new();
        await foreach (ChatCompletionResponse update in responseStream)
        {
            yield return TranslateStreamingUpdate(accumulator, update);
        }
    }

    public void Dispose()
    {
        Interlocked.Exchange(ref this._anthropicClient, null)?.Dispose();
    }

    public TService? GetService<TService>(object? key = null) where TService : class
    {
        // Implement this based on the example in the M.E.AI.OpenAI implementation
        // see: https://github.com/dotnet/extensions/blob/main/src/Libraries/Microsoft.Extensions.AI.OpenAI/OpenAIChatClient.cs#L95-L105

        if (key != null)
        {
            return null;
        }

        if (this is TService result)
        {
            return result;
        }

        if (typeof(TService).IsAssignableFrom(typeof(AnthropicClient)))
        {
            return (TService)(object)this._anthropicClient!;
        }

        return null;
    }
}
