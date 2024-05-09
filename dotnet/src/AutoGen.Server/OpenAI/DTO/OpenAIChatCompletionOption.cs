// Copyright (c) Microsoft Corporation. All rights reserved.
// Class.cs

using System;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace AutoGen.Service.OpenAI.DTO;

[JsonConverter(typeof(OpenAIMessageConverter))]
public abstract class OpenAIMessage
{
    [JsonPropertyName("role")]
    public abstract string? Role { get; }
}

public class OpenAISystemMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "system";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}

public class OpenAIUserMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "user";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}

public interface IOpenAIUserMessageItem
{
    [JsonPropertyName("type")]
    public string MessageType { get; set; }
}

public class OpenAIUserTextContent : IOpenAIUserMessageItem
{
    [JsonPropertyName("type")]
    public string MessageType { get; set; } = "text";

    [JsonPropertyName("text")]
    public string? Content { get; set; }
}

public class OpenAIImageUrlObject
{
    [JsonPropertyName("url")]
    public string? Url { get; set; }

    [JsonPropertyName("detail")]
    public string? Detail { get; set; } = "auto";
}

public class OpenAIUserImageContent : IOpenAIUserMessageItem
{
    [JsonPropertyName("type")]
    public string MessageType { get; set; } = "image";

    [JsonPropertyName("image_url")]
    public string? Url { get; set; }
}

public class OpenAIUserMultiModalMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "user";

    [JsonPropertyName("content")]
    public IOpenAIUserMessageItem[]? Content { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}

public class OpenAIToolCallObject
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("arguments")]
    public string? Arguments { get; set; }
}

public class OpenAIAssistantMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "assistant";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("tool_calls")]
    public OpenAIToolCallObject[]? ToolCalls { get; set; }
}

public class OpenAIToolMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "tool";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("tool_call_id")]
    public string? ToolCallId { get; set; }
}

public class OpenAIMessageConverter : JsonConverter<OpenAIMessage>
{
    public override OpenAIMessage Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        using JsonDocument document = JsonDocument.ParseValue(ref reader);
        var root = document.RootElement;
        var role = root.GetProperty("role").GetString();
        var contentDocument = root.GetProperty("content");
        var isContentDocumentString = contentDocument.ValueKind == JsonValueKind.String;
        switch (role)
        {
            case "system":
                return JsonSerializer.Deserialize<OpenAISystemMessage>(root.GetRawText()) ?? throw new JsonException();
            case "user" when isContentDocumentString:
                return JsonSerializer.Deserialize<OpenAIUserMessage>(root.GetRawText()) ?? throw new JsonException();
            case "user" when !isContentDocumentString:
                return JsonSerializer.Deserialize<OpenAIUserMultiModalMessage>(root.GetRawText()) ?? throw new JsonException();
            case "assistant":
                return JsonSerializer.Deserialize<OpenAIAssistantMessage>(root.GetRawText()) ?? throw new JsonException();
            case "tool":
                return JsonSerializer.Deserialize<OpenAIToolMessage>(root.GetRawText()) ?? throw new JsonException();
            default:
                throw new JsonException();
        }
    }

    public override void Write(Utf8JsonWriter writer, OpenAIMessage value, JsonSerializerOptions options)
    {
        switch (value)
        {
            case OpenAISystemMessage systemMessage:
                JsonSerializer.Serialize(writer, systemMessage, options);
                break;
            case OpenAIUserMessage userMessage:
                JsonSerializer.Serialize(writer, userMessage, options);
                break;
            case OpenAIAssistantMessage assistantMessage:
                JsonSerializer.Serialize(writer, assistantMessage, options);
                break;
            case OpenAIToolMessage toolMessage:
                JsonSerializer.Serialize(writer, toolMessage, options);
                break;
            default:
                throw new JsonException();
        }
    }
}

public class OpenAIChatCompletionOption
{
    [JsonPropertyName("messages")]
    public OpenAIMessage[]? Messages { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("max_tokens")]
    public int? MaxTokens { get; set; }

    [JsonPropertyName("temperature")]
    public float Temperature { get; set; } = 1;
}

public class OpenAIChatCompletionUsage
{
    [JsonPropertyName("completion_tokens")]
    public int CompletionTokens { get; set; }

    [JsonPropertyName("prompt_tokens")]
    public int PromptTokens { get; set; }

    [JsonPropertyName("total_tokens")]
    public int TotalTokens { get; set; }
}

public class OpenAIChatCompletionMessage
{
    [JsonPropertyName("role")]
    public string Role { get; } = "assistant";

    [JsonPropertyName("content")]
    public string? Content { get; set; }
}

public class OpenAIChatCompletionChoice
{
    [JsonPropertyName("finish_reason")]
    public string? FinishReason { get; set; }

    [JsonPropertyName("index")]
    public int Index { get; set; }

    [JsonPropertyName("message")]
    public OpenAIChatCompletionMessage? Message { get; set; }
}

public class OpenAIChatCompletion
{
    [JsonPropertyName("id")]
    public string? ID { get; set; }

    [JsonPropertyName("created")]
    public long Created { get; set; }

    [JsonPropertyName("choices")]
    public OpenAIChatCompletionChoice[]? Choices { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("system_fingerprint")]
    public string? SystemFingerprint { get; set; }

    [JsonPropertyName("object")]
    public string Object { get; set; } = "chat.completion";

    [JsonPropertyName("usage")]
    public OpenAIChatCompletionUsage? Usage { get; set; }
}
