// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionExtension.cs

using AutoGen.SourceGenerator;

internal static class FunctionExtension
{
    public static string GetFunctionName(this SourceGeneratorFunctionContract function)
    {
        return function.Name ?? string.Empty;
    }

    public static string GetFunctionSchemaClassName(this SourceGeneratorFunctionContract function)
    {
        return $"{function.GetFunctionName()}Schema";
    }

    public static string GetFunctionDefinitionName(this SourceGeneratorFunctionContract function)
    {
        return $"{function.GetFunctionName()}Function";
    }

    public static string GetFunctionWrapperName(this SourceGeneratorFunctionContract function)
    {
        return $"{function.GetFunctionName()}Wrapper";
    }

    public static string GetFunctionContractName(this SourceGeneratorFunctionContract function)
    {
        return $"{function.GetFunctionName()}FunctionContract";
    }
}
