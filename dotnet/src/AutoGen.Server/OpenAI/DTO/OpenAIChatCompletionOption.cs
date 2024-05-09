// Copyright (c) Microsoft Corporation. All rights reserved.
// Class.cs

using System.Text.Json.Serialization;

namespace AutoGen.Service.OpenAI.DTO;

public abstract class OpenAIMessage
{
}

public class OpenAISystemMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public string? Role { get; set; } = "system";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}

public class OpenAIUserMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public string? Role { get; set; } = "user";

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
    public string? Role { get; set; } = "user";

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
    public string? Role { get; set; } = "assistant";

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
    public string? Role { get; set; } = "tool";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("tool_call_id")]
    public string? ToolCallId { get; set; }
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
    public double? Temperature { get; set; } = 1;
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
    public string Role { get; set; } = "assistant";

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
    public int Created { get; set; }

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
