// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionAttribute.cs

using System;

namespace AutoGen;

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
