// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionAttribute.cs

using System;
using System.Collections.Generic;
using System.Linq;
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

    public static implicit operator FunctionContract(AIFunctionMetadata metadata)
    {
        return new FunctionContract
        {
            Namespace = metadata.AdditionalProperties.ContainsKey(NamespaceKey) ? metadata.AdditionalProperties[NamespaceKey] as string : null,
            ClassName = metadata.AdditionalProperties.ContainsKey(ClassNameKey) ? metadata.AdditionalProperties[ClassNameKey] as string : null,
            Name = metadata.Name,
            Description = metadata.Description,
            Parameters = metadata.Parameters?.Select(p => (FunctionParameterContract)p).ToList(),
            ReturnType = metadata.ReturnParameter.ParameterType,
            ReturnDescription = metadata.ReturnParameter.Description,
        };
    }

    public static implicit operator AIFunctionMetadata(FunctionContract contract)
    {
        return new AIFunctionMetadata(contract.Name)
        {
            Description = contract.Description,
            ReturnParameter = new AIFunctionReturnParameterMetadata()
            {
                Description = contract.ReturnDescription,
                ParameterType = contract.ReturnType,
            },
            AdditionalProperties = new Dictionary<string, object?>
            {
                [NamespaceKey] = contract.Namespace,
                [ClassNameKey] = contract.ClassName,
            },
            Parameters = [.. contract.Parameters?.Select(p => (AIFunctionParameterMetadata)p)],
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

    // convert to/from FunctionParameterMetadata
    public static implicit operator FunctionParameterContract(AIFunctionParameterMetadata metadata)
    {
        return new FunctionParameterContract
        {
            Name = metadata.Name,
            Description = metadata.Description,
            ParameterType = metadata.ParameterType,
            IsRequired = metadata.IsRequired,
            DefaultValue = metadata.DefaultValue,
        };
    }

    public static implicit operator AIFunctionParameterMetadata(FunctionParameterContract contract)
    {
        return new AIFunctionParameterMetadata(contract.Name!)
        {
            DefaultValue = contract.DefaultValue,
            Description = contract.Description,
            IsRequired = contract.IsRequired,
            ParameterType = contract.ParameterType,
            HasDefaultValue = contract.DefaultValue != null,
        };
    }
}
