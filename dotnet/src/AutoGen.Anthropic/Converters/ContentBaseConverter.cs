// Copyright (c) Microsoft Corporation. All rights reserved.
// ContentBaseConverter.cs

using System;
using System.Text.Json;
using System.Text.Json.Serialization;
using AutoGen.Anthropic.DTO;
namespace AutoGen.Anthropic.Converters;

public sealed class ContentBaseConverter : JsonConverter<ContentBase>
{
    public override ContentBase Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        using var doc = JsonDocument.ParseValue(ref reader);
        if (doc.RootElement.TryGetProperty("type", out JsonElement typeProperty) && !string.IsNullOrEmpty(typeProperty.GetString()))
        {
            string? type = typeProperty.GetString();
            var text = doc.RootElement.GetRawText();
            switch (type)
            {
                case "text":
                    return JsonSerializer.Deserialize<TextContent>(text, options) ?? throw new InvalidOperationException();
                case "image":
                    return JsonSerializer.Deserialize<ImageContent>(text, options) ?? throw new InvalidOperationException();
                case "tool_use":
                    return JsonSerializer.Deserialize<ToolUseContent>(text, options) ?? throw new InvalidOperationException();
                case "tool_result":
                    return JsonSerializer.Deserialize<ToolResultContent>(text, options) ?? throw new InvalidOperationException();
            }
        }

        throw new JsonException("Unknown content type");
    }

    public override void Write(Utf8JsonWriter writer, ContentBase value, JsonSerializerOptions options)
    {
        JsonSerializer.Serialize(writer, value, value.GetType(), options);
    }
}
