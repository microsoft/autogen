// Copyright (c) Microsoft Corporation. All rights reserved.
// Tool.cs

using System.Text.Json.Serialization;
using Microsoft.Extensions.AI;

namespace AutoGen.Anthropic.DTO;

public class Tool
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("input_schema")]
    public InputSchema? InputSchema { get; set; }

    [JsonPropertyName("cache_control")]
    public CacheControl? CacheControl { get; set; }

    // Implicit conversion operator from M.E.AI.AITool to Tool
    public static implicit operator Tool(Microsoft.Extensions.AI.AIFunction tool)
    {
        return new Tool
        {
            Name = tool.Metadata.Name,
            Description = tool.Metadata.Description,
            InputSchema = InputSchema.ExtractSchema(tool),
            //CacheControl = null
        };
    }
}

public class InputSchema
{
    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("properties")]
    public Dictionary<string, SchemaProperty>? Properties { get; set; }

    [JsonPropertyName("required")]
    public List<string>? Required { get; set; }

    public static InputSchema ExtractSchema(AIFunction tool) => ExtractSchema(tool.Metadata.Parameters);

    private static InputSchema ExtractSchema(IReadOnlyList<AIFunctionParameterMetadata> parameterMetadata)
    {
        List<string> required = new List<string>();
        Dictionary<string, SchemaProperty> properties = new Dictionary<string, SchemaProperty>();

        foreach (AIFunctionParameterMetadata parameter in parameterMetadata)
        {
            properties.Add(parameter.Name, new SchemaProperty { Type = parameter.ParameterType?.Name, Description = parameter.Description });
            if (parameter.IsRequired)
            {
                required.Add(parameter.Name);
            }
        }

        return new InputSchema { Type = "object", Properties = properties, Required = required };
    }
}

public class SchemaProperty
{
    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }
}
