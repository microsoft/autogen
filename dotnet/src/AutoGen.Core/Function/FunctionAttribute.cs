// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionAttribute.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.AI;

namespace AutoGen.Core;

[AttributeUsage(AttributeTargets.Method, Inherited = false, AllowMultiple = false)]
public class FunctionAttribute : Attribute
{
    public string? FunctionName { get; }

    public string? Description { get; }

    public FunctionAttribute(string? functionName = null, string? description = null)
    {
        FunctionName = functionName;
        Description = description;
    }
}

public class FunctionContract
{
    private const string NamespaceKey = nameof(Namespace);

    private const string ClassNameKey = nameof(ClassName);

    /// <summary>
    /// The namespace of the function.
    /// </summary>
    public string? Namespace { get; set; }

    /// <summary>
    /// The class name of the function.
    /// </summary>
    public string? ClassName { get; set; }

    /// <summary>
    /// The name of the function.
    /// </summary>
    public string Name { get; set; } = null!;

    /// <summary>
    /// The description of the function.
    /// If a structured comment is available, the description will be extracted from the summary section.
    /// Otherwise, the description will be null.
    /// </summary>
    public string? Description { get; set; }

    /// <summary>
    /// The parameters of the function.
    /// </summary>
    public IEnumerable<FunctionParameterContract>? Parameters { get; set; }

    /// <summary>
    /// The return type of the function.
    /// </summary>
    [JsonIgnore]
    public Type? ReturnType { get; set; }

    /// <summary>
    /// The description of the return section.
    /// If a structured comment is available, the description will be extracted from the return section.
    /// Otherwise, the description will be null.
    /// </summary>
    public string? ReturnDescription { get; set; }

    public static implicit operator FunctionContract(AIFunction function)
    {
        var openapiScheme = function.JsonSchema;
        var parameters = new List<FunctionParameterContract>();
        string[] isRequiredProperties = [];
        if (openapiScheme.TryGetProperty("required", out var requiredElement))
        {
            isRequiredProperties = requiredElement.Deserialize<string[]>() ?? [];
        }

        var parameterList = function.UnderlyingMethod?.GetParameters() ?? Array.Empty<ParameterInfo>();

        if (openapiScheme.TryGetProperty("properties", out var propertiesElement))
        {
            var properties = propertiesElement.Deserialize<Dictionary<string, JsonElement>>() ?? new Dictionary<string, JsonElement>();
            foreach (var property in properties)
            {
                var parameterType = parameterList.FirstOrDefault(p => p.Name == property.Key)?.ParameterType;
                var parameter = new FunctionParameterContract
                {
                    Name = property.Key,
                    ParameterType = parameterType, // TODO: Need to get the type from the schema
                    IsRequired = isRequiredProperties.Contains(property.Key),
                };
                if (property.Value.TryGetProperty("description", out var descriptionElement))
                {
                    parameter.Description = descriptionElement.GetString();
                }
                if (property.Value.TryGetProperty("default", out var defaultValueElement))
                {
                    parameter.DefaultValue = defaultValueElement.Deserialize<object>();
                }
                parameters.Add(parameter);
            }
        }
        return new FunctionContract
        {
            Namespace = function.AdditionalProperties.ContainsKey(NamespaceKey) ? function.AdditionalProperties[NamespaceKey] as string : null,
            ClassName = function.AdditionalProperties.ContainsKey(ClassNameKey) ? function.AdditionalProperties[ClassNameKey] as string : null,
            Name = function.Name,
            Description = function.Description,
            Parameters = parameters,
        };
    }
}

public class FunctionParameterContract
{
    /// <summary>
    /// The name of the parameter.
    /// </summary>
    public string? Name { get; set; }

    /// <summary>
    /// The description of the parameter.
    /// This will be extracted from the param section of the structured comment if available.
    /// Otherwise, the description will be null.
    /// </summary>
    public string? Description { get; set; }

    /// <summary>
    /// The type of the parameter.
    /// </summary>
    [JsonIgnore]
    public Type? ParameterType { get; set; }

    /// <summary>
    /// If the parameter is a required parameter.
    /// </summary>
    public bool IsRequired { get; set; }

    /// <summary>
    /// The default value of the parameter.
    /// </summary>
    public object? DefaultValue { get; set; }
}
