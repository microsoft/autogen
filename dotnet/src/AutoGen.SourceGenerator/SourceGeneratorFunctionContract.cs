// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// SourceGeneratorFunctionContract.cs

namespace AutoGen.SourceGenerator
{
    internal class SourceGeneratorFunctionContract
    {
        public string? Namespace { get; set; }

        public string? ClassName { get; set; }

        public string? Name { get; set; }

        public string? Description { get; set; }

        public string? ReturnDescription { get; set; }

        public SourceGeneratorParameterContract[]? Parameters { get; set; }

        public string? ReturnType { get; set; }
    }

    internal class SourceGeneratorParameterContract
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
