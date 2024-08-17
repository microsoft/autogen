// Copyright (c) Microsoft Corporation. All rights reserved.
// Tools.cs

using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class Tool
{
    [JsonPropertyName("type")]
    public string? Type { get; set; } = "function";

    [JsonPropertyName("function")]
    public Function? Function { get; set; }
}

public class Function
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("parameters")]
    public Parameters? Parameters { get; set; }
}

public class Parameters
{
    [JsonPropertyName("type")]
    public string? Type { get; set; } = "object";

    [JsonPropertyName("properties")]
    public Dictionary<string, Properties>? Properties { get; set; }

    [JsonPropertyName("required")]
    public IEnumerable<string>? Required { get; set; }
}

public class Properties
{
    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("enum")]
    public IEnumerable<string>? Enum { get; set; }
}
