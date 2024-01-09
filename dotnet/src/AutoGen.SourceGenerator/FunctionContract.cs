// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionContract.cs

namespace AutoGen.SourceGenerator
{
    internal class FunctionContract
    {
        public string? Name { get; set; }

        public string? Description { get; set; }

        public ParameterContract[]? Parameters { get; set; }

        public string? ReturnType { get; set; }

        public bool IsAsync { get; set; }
    }

    internal class ParameterContract
    {
        public string? Name { get; set; }

        public string? Description { get; set; }

        public string? JsonType { get; set; }

        public string? JsonItemType { get; set; }

        public string? Type { get; set; }

        public bool IsOptional { get; set; }

        public string? DefaultValue { get; set; }

    }
}
