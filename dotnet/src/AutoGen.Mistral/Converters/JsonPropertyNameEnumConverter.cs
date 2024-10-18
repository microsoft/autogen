// Copyright (c) Microsoft Corporation. All rights reserved.
// JsonPropertyNameEnumConverter.cs

using System;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

internal sealed class JsonPropertyNameEnumConverter<T> : JsonConverter<T> where T : struct, Enum
{
    public override T Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        string value = reader.GetString() ?? throw new JsonException("Value was null.");

        foreach (var field in typeToConvert.GetFields())
        {
            var attribute = field.GetCustomAttribute<JsonPropertyNameAttribute>();
            if (attribute?.Name == value)
            {
                return (T)Enum.Parse(typeToConvert, field.Name);
            }
        }

        throw new JsonException($"Unable to convert \"{value}\" to enum {typeToConvert}.");
    }

    public override void Write(Utf8JsonWriter writer, T value, JsonSerializerOptions options)
    {
        var field = value.GetType().GetField(value.ToString());
        var attribute = field?.GetCustomAttribute<JsonPropertyNameAttribute>();

        if (attribute != null)
        {
            writer.WriteStringValue(attribute.Name);
        }
        else
        {
            writer.WriteStringValue(value.ToString());
        }
    }
}
