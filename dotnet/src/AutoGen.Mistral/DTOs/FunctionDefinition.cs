// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionDefinition.cs

using System.Text.Json.Serialization;
using Json.Schema;

namespace AutoGen.Mistral;

public class FunctionDefinition
{
    public FunctionDefinition(string name, string description, JsonSchema? parameters = default)
    {
        Name = name;
        Description = description;
        Parameters = parameters;
    }

    [JsonPropertyName("name")]
    public string Name { get; set; }

    [JsonPropertyName("description")]
    public string Description { get; set; }

    [JsonPropertyName("parameters")]
    public JsonSchema? Parameters { get; set; }
}
