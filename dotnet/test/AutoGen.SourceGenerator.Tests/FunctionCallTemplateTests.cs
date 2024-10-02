// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionCallTemplateTests.cs

using ApprovalTests;
using ApprovalTests.Namers;
using ApprovalTests.Reporters;
using AutoGen.SourceGenerator.Template;
using Xunit;

namespace AutoGen.SourceGenerator.Tests;

public class FunctionCallTemplateTests
{
    [Fact]
    [UseReporter(typeof(DiffReporter))]
    [UseApprovalSubdirectory("ApprovalTests")]
    public void TestFunctionCallTemplate()
    {
        var functionExample = new FunctionExamples();
        var function = functionExample.AddAsyncFunctionContract;
        var functionCallTemplate = new FunctionCallTemplate()
        {
            ClassName = function.ClassName,
            NameSpace = function.Namespace,
            FunctionContracts = [new SourceGeneratorFunctionContract()
            {
                Name = function.Name,
                Description = function.Description,
                ReturnType = function.ReturnType!.ToString(),
                ReturnDescription = function.ReturnDescription,
                Parameters = function.Parameters!.Select(p => new SourceGeneratorParameterContract()
                {
                    Name = p.Name,
                    Description = p.Description,
                    Type = p.ParameterType!.ToString(),
                    IsOptional = !p.IsRequired,
                    JsonType = p.ParameterType!.ToString(),
                }).ToArray()
            }]
        };

        var actual = functionCallTemplate.TransformText();

        Approvals.Verify(actual);
    }
}
