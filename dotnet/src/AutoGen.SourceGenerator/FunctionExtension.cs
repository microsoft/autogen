// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionExtension.cs

using AutoGen.SourceGenerator;

internal static class FunctionExtension
{
    public static string GetFunctionName(this FunctionContract function)
    {
        return function.Name ?? string.Empty;
    }

    public static string GetFunctionSchemaClassName(this FunctionContract function)
    {
        return $"{function.GetFunctionName()}Schema";
    }

    public static string GetFunctionDefinitionName(this FunctionContract function)
    {
        return $"{function.GetFunctionName()}Function";
    }

    public static string GetFunctionWrapperName(this FunctionContract function)
    {
        return $"{function.GetFunctionName()}Wrapper";
    }

    public static string GetFunctionContractName(this FunctionContract function)
    {
        return $"{function.GetFunctionName()}FunctionContract";
    }
}
