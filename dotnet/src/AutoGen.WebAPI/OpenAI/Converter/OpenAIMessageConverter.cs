// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIMessageConverter.cs

using System;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace AutoGen.Service.OpenAI.DTO;

internal class OpenAIMessageConverter : JsonConverter<OpenAIMessage>
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
