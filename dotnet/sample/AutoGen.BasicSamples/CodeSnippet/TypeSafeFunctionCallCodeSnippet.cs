// Copyright (c) Microsoft Corporation. All rights reserved.
// TypeSafeFunctionCallCodeSnippet.cs

using System.Text.Json;
using AutoGen;
using Azure.AI.OpenAI;

#region code_snippet_3
// file: FunctionCall.cs

public partial class TypeSafeFunctionCall
{
    /// <summary>
    /// convert input to upper case 
    /// </summary>
    /// <param name="input">input</param>
    [Function]
    public async Task<string> UpperCase(string input)
    {
        var result = input.ToUpper();
        return result;
    }
}
#endregion code_snippet_3

public class TypeSafeFunctionCallCodeSnippet
{
    public async Task<string> UpperCase(string input)
    {
        var result = input.ToUpper();
        return result;
    }

    #region code_snippet_1
    // file: FunctionDefinition.generated.cs
    public FunctionDefinition UpperCaseFunction
    {
        get => new FunctionDefinition
        {
            Name = @"UpperCase",
            Description = "convert input to upper case",
            Parameters = BinaryData.FromObjectAsJson(new
            {
                Type = "object",
                Properties = new
                {
                    input = new
                    {
                        Type = @"string",
                        Description = @"input",
                    },
                },
                Required = new[]
                {
                        "input",
                    },
            },
            new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            })
        };
    }
    #endregion code_snippet_1

    #region code_snippet_2
    // file: FunctionDefinition.generated.cs
    private class UpperCaseSchema
    {
        public string input { get; set; }
    }

    public Task<string> UpperCaseWrapper(string arguments)
    {
        var schema = JsonSerializer.Deserialize<UpperCaseSchema>(
            arguments,
            new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            });

        return UpperCase(schema.input);
    }
    #endregion code_snippet_2
}
