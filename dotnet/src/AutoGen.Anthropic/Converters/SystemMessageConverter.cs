// Copyright (c) Microsoft Corporation. All rights reserved.
// SystemMessageConverter.cs

using System;
using System.Text.Json;
using System.Text.Json.Serialization;
using AutoGen.Anthropic.DTO;

namespace AutoGen.Anthropic.Converters;

public class SystemMessageConverter : JsonConverter<object>
{
    public override object Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType == JsonTokenType.String)
        {
            return reader.GetString() ?? string.Empty;
        }
        if (reader.TokenType == JsonTokenType.StartArray)
        {
            return JsonSerializer.Deserialize<SystemMessage[]>(ref reader, options) ?? throw new InvalidOperationException();
        }

        throw new JsonException();
    }

    public override void Write(Utf8JsonWriter writer, object value, JsonSerializerOptions options)
    {
        if (value is string stringValue)
        {
            writer.WriteStringValue(stringValue);
        }
        else if (value is SystemMessage[] arrayValue)
        {
            JsonSerializer.Serialize(writer, arrayValue, options);
        }
        else
        {
            throw new JsonException();
        }
    }
}
