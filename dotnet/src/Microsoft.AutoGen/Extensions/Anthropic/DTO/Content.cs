// Copyright (c) Microsoft Corporation. All rights reserved.
// Content.cs

using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using AutoGen.Anthropic.Converters;

namespace AutoGen.Anthropic.DTO;

public static class AIContentExtensions
{
    public static string? ToBase64String(this ReadOnlyMemory<byte>? data)
    {
        if (data == null)
        {
            return null;
        }

        // TODO: reduce the numbers of copies here ( .ToArray() + .ToBase64String() )
        return Convert.ToBase64String(data.Value.ToArray());
    }

    public static byte[]? FromBase64String(this string? data)
    {
        if (data == null)
        {
            return null;
        }

        return Convert.FromBase64String(data);
    }
}

public abstract class ContentBase
{
    [JsonPropertyName("type")]
    public abstract string Type { get; }

    [JsonPropertyName("cache_control")]
    public CacheControl? CacheControl { get; set; }

    public static implicit operator ContentBase(Microsoft.Extensions.AI.AIContent content)
    {
        return content switch
        {
            Microsoft.Extensions.AI.TextContent textContent => (TextContent)textContent,
            Microsoft.Extensions.AI.ImageContent imageContent => (ImageContent)imageContent,
            Microsoft.Extensions.AI.FunctionCallContent functionCallContent => (ToolUseContent)functionCallContent,
            Microsoft.Extensions.AI.FunctionResultContent functionResultContent => (ToolResultContent)functionResultContent,
            _ => throw new NotSupportedException($"Unsupported content type: {content.GetType()}")
        };
    }

    public static implicit operator Microsoft.Extensions.AI.AIContent(ContentBase content)
    {
        return content switch
        {
            TextContent textContent => (Microsoft.Extensions.AI.TextContent)textContent,
            ImageContent imageContent => (Microsoft.Extensions.AI.ImageContent)imageContent,
            ToolUseContent toolUseContent => (Microsoft.Extensions.AI.FunctionCallContent)toolUseContent,
            ToolResultContent toolResultContent => (Microsoft.Extensions.AI.FunctionResultContent)toolResultContent,
            _ => throw new NotSupportedException($"Unsupported content type: {content.GetType()}")
        };
    }
}

public class TextContent : ContentBase
{
    [JsonPropertyName("type")]
    public override string Type => "text";

    [JsonPropertyName("text")]
    public string? Text { get; set; }

    public static TextContent CreateTextWithCacheControl(string text) => new()
    {
        Text = text,
        CacheControl = new CacheControl { Type = CacheControlType.Ephemeral }
    };

    public static implicit operator TextContent(Microsoft.Extensions.AI.TextContent textContent)
    {
        return new TextContent { Text = textContent.Text };
    }

    public static implicit operator Microsoft.Extensions.AI.TextContent(TextContent textContent)
    {
        return new Microsoft.Extensions.AI.TextContent(textContent.Text)
        {
            RawRepresentation = textContent
        };
    }
}

public class ImageContent : ContentBase
{
    [JsonPropertyName("type")]
    public override string Type => "image";

    [JsonPropertyName("source")]
    public ImageSource? Source { get; set; }

    public static implicit operator ImageContent(Microsoft.Extensions.AI.ImageContent imageContent)
    {
        ImageSource source = new ImageSource
        {
            MediaType = imageContent.MediaType,
        };

        if (imageContent.ContainsData)
        {
            source.Data = imageContent.Data.ToBase64String();
        }

        return new ImageContent
        {
            Source = source,
        };
    }

    public static implicit operator Microsoft.Extensions.AI.ImageContent(ImageContent imageContent)
    {
        ReadOnlyMemory<byte> imageData = imageContent.Source?.Data.FromBase64String() ?? [];

        return new Microsoft.Extensions.AI.ImageContent(imageData, mediaType: imageContent.Source?.MediaType)
        {
            RawRepresentation = imageContent
        };
    }
}

public class ImageSource
{
    [JsonPropertyName("type")]
    public string Type => "base64";

    [JsonPropertyName("media_type")]
    public string? MediaType { get; set; }

    [JsonPropertyName("data")]
    public string? Data { get; set; }
}

public class ToolUseContent : ContentBase
{
    [JsonPropertyName("type")]
    public override string Type => "tool_use";

    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("input")]
    public JsonNode? Input { get; set; }

    public static implicit operator ToolUseContent(Microsoft.Extensions.AI.FunctionCallContent functionCallContent)
    {
        JsonNode? input = functionCallContent.Arguments != null ? JsonSerializer.SerializeToNode(functionCallContent.Arguments) : null;

        return new ToolUseContent
        {
            Id = functionCallContent.CallId,
            Name = functionCallContent.Name,
            Input = input
        };
    }

    public static implicit operator Microsoft.Extensions.AI.FunctionCallContent(ToolUseContent toolUseContent)
    {
        // These are an unfortunate incompatibilty between the two libraries (for now); later we can work to
        // parse the JSON directly into the M.E.AI types
        if (toolUseContent.Id == null)
        {
            throw new ArgumentNullException(nameof(toolUseContent.Id));
        }

        if (toolUseContent.Name == null)
        {
            throw new ArgumentNullException(nameof(toolUseContent.Name));
        }

        IDictionary<string, object?>? arguments = null;
        if (toolUseContent.Input != null)
        {
            arguments = JsonSerializer.Deserialize<IDictionary<string, object?>>(toolUseContent.Input);
        }

        return new Microsoft.Extensions.AI.FunctionCallContent(toolUseContent.Id, toolUseContent.Name, arguments)
        {
            RawRepresentation = toolUseContent
        };
    }
}

public class ToolResultContent : ContentBase
{
    [JsonPropertyName("type")]
    public override string Type => "tool_result";

    [JsonPropertyName("tool_use_id")]
    public string? Id { get; set; }

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("is_error")]
    public bool IsError { get; set; }

    public static implicit operator ToolResultContent(Microsoft.Extensions.AI.FunctionResultContent functionResultContent)
    {
        // If the result is successful, convert the return object (if any) to the content string
        // Otherwise, convert the error message to the content string
        string? content = null;
        if (functionResultContent.Exception != null)
        {
            // TODO: Technically, .Result should also contain the error message?
            content = functionResultContent.Exception.Message;
        }
        else if (functionResultContent.Result != null)
        {
            // If the result is a string, it should just be a passthrough (with enquotation)
            content = JsonSerializer.Serialize(functionResultContent.Result);
        }

        return new ToolResultContent
        {
            Id = functionResultContent.CallId,
            Content = content,
            IsError = functionResultContent.Exception != null
        };
    }

    public static implicit operator Microsoft.Extensions.AI.FunctionResultContent(ToolResultContent toolResultContent)
    {
        if (toolResultContent.Id == null)
        {
            throw new ArgumentNullException(nameof(toolResultContent.Id));
        }

        // If the content is a string, it should be deserialized as a string
        object? result = null;
        if (toolResultContent.Content != null)
        {
            // TODO: Unfortunately, there is no way to get back to the exception from the content,
            // since ToolCallResult does not encode a way to determine success from failure
            result = JsonSerializer.Deserialize<object>(toolResultContent.Content);
        }

        Exception? error = null;
        if (toolResultContent.IsError)
        {
            error = new Exception(toolResultContent.Content);
        }

        // TODO: Should we model the name on this object?
        return new Microsoft.Extensions.AI.FunctionResultContent(toolResultContent.Id, "", result)
        {
            Exception = error,
            RawRepresentation = toolResultContent
        };
    }
}

public class CacheControl
{
    [JsonPropertyName("type")]
    public CacheControlType Type { get; set; }

    public static CacheControl Create() => new CacheControl { Type = CacheControlType.Ephemeral };
}

[JsonConverter(typeof(JsonPropertyNameEnumConverter<CacheControlType>))]
public enum CacheControlType
{
    [JsonPropertyName("ephemeral")]
    Ephemeral
}
