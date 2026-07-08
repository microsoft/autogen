// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatRequest.cs

using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class ChatRequest
{
    /// <summary>
    /// (required) the model name
    /// </summary>
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    /// <summary>
    /// the messages of the chat, this can be used to keep a chat memory
    /// </summary>
    [JsonPropertyName("messages")]
    public IList<Message> Messages { get; set; } = [];

    /// <summary>
    /// the format to return a response in. Currently, the only accepted value is json
    /// </summary>
    [JsonPropertyName("format")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Format { get; set; }

    /// <summary>
    /// additional model parameters listed in the documentation for the Modelfile such as temperature
    /// </summary>
    [JsonPropertyName("options")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ModelReplyOptions? Options { get; set; }
    /// <summary>
    /// the prompt template to use (overrides what is defined in the Modelfile)
    /// </summary>
    [JsonPropertyName("template")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Template { get; set; }
    /// <summary>
    /// if false the response will be returned as a single response object, rather than a stream of objects
    /// </summary>
    [JsonPropertyName("stream")]
    public bool Stream { get; set; }
    /// <summary>
    /// controls how long the model will stay loaded into memory following the request (default: 5m)
    /// </summary>
    [JsonPropertyName("keep_alive")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? KeepAlive { get; set; }
}
