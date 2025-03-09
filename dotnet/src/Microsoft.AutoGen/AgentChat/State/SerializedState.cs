// Copyright (c) Microsoft Corporation. All rights reserved.
// SerializedState.cs

using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.State;

public class SerializedStateConverter : JsonConverter<SerializedState>
{
    public override SerializedState Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var json = JsonDocument.ParseValue(ref reader).RootElement;
        var state = new SerializedState(json);
        return state;
    }

    public override void Write(Utf8JsonWriter writer, SerializedState value, JsonSerializerOptions options)
    {
        value.AsJson().WriteTo(writer);
    }
}

[JsonConverter(typeof(SerializedStateConverter))]
public class SerializedState
{
    private readonly JsonSerializerOptions SerializerOptions = new()
    {
        Converters =
        {
            new SerializedStateConverter(),
        },
        TypeInfoResolver = new MessageSerializationHelpers.MessagesTypeInfoResolver(),
    };

    public JsonElement AsJson()
    {
        if (this.jsonValue != null)
        {
            return this.jsonValue.Value;
        }

        if (this.deserializedValue == null)
        {
            throw new InvalidOperationException("State is not initialized.");
        }

        this.jsonValue = JsonSerializer.SerializeToElement(this.deserializedValue, SerializerOptions);
        return this.jsonValue.Value;
    }

    public static SerializedState Create<T>(T state) where T : notnull
    {
        return new SerializedState((object)state);
    }

    public T As<T>()
    {
        if (this.deserializedValue is T value)
        {
            return value;
        }

        if (this.deserializedValue != null)
        {
            throw new InvalidOperationException($"Cannot convert state of type {this.deserializedValue.GetType()} to {typeof(T)}.");
        }

        if (this.jsonValue == null)
        {
            throw new InvalidOperationException("State is not initialized.");
        }

        T? result = JsonSerializer.Deserialize<T>(this.jsonValue!.Value, SerializerOptions)
                    ?? throw new InvalidOperationException($"Cannot deserialize state to {typeof(T)}.");

        this.deserializedValue = result;

        return result;
    }

    private object? deserializedValue;
    private JsonElement? jsonValue;

    private SerializedState(object state)
    {
        this.deserializedValue = state;
    }

    public SerializedState(JsonElement json)
    {
        this.jsonValue = json;
    }

    public static implicit operator SerializedState(JsonElement json)
    {
        return new SerializedState(json);
    }
}
