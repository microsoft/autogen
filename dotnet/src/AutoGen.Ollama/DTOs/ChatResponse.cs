// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatResponse.cs

using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class ChatResponse : ChatResponseUpdate
{
    /// <summary>
    /// time spent generating the response
    /// </summary>
    [JsonPropertyName("total_duration")]
    public long TotalDuration { get; set; }

    /// <summary>
    /// time spent in nanoseconds loading the model
    /// </summary>
    [JsonPropertyName("load_duration")]
    public long LoadDuration { get; set; }

    /// <summary>
    /// number of tokens in the prompt
    /// </summary>
    [JsonPropertyName("prompt_eval_count")]
    public int PromptEvalCount { get; set; }

    /// <summary>
    /// time spent in nanoseconds evaluating the prompt
    /// </summary>
    [JsonPropertyName("prompt_eval_duration")]
    public long PromptEvalDuration { get; set; }

    /// <summary>
    /// number of tokens the response
    /// </summary>
    [JsonPropertyName("eval_count")]
    public int EvalCount { get; set; }

    /// <summary>
    /// time in nanoseconds spent generating the response
    /// </summary>
    [JsonPropertyName("eval_duration")]
    public long EvalDuration { get; set; }
}
