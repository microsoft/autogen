// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionAttribution.cs

using System;

namespace AutoGen
{
    [AttributeUsage(AttributeTargets.Method, Inherited = false, AllowMultiple = false)]
    public class FunctionAttribution : Attribute
    {
        public string? FunctionName { get; }

        public string? Description { get; }

        public FunctionAttribution(string? functionName = null, string? description = null)
        {
            FunctionName = functionName;
            Description = description;
        }
    }
}
