// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionAttribute.cs

using System;
using System.Collections.Generic;

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
    public Type? ReturnType { get; set; }

    /// <summary>
    /// The description of the return section.
    /// If a structured comment is available, the description will be extracted from the return section.
    /// Otherwise, the description will be null.
    /// </summary>
    public string? ReturnDescription { get; set; }
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
