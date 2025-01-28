// Copyright (c) Microsoft Corporation. All rights reserved.
// TypeSafeFunctionCallCodeSnippet.cs

using System.Text.Json;
using AutoGen.OpenAI.Extension;
#region weather_report_using_statement
using AutoGen.Core;
#endregion weather_report_using_statement

#region weather_report
public partial class TypeSafeFunctionCall
{
    /// <summary>
    /// Get weather report
    /// </summary>
    /// <param name="city">city</param>
    /// <param name="date">date</param>
    [Function]
    public async Task<string> WeatherReport(string city, string date)
    {
        return $"Weather report for {city} on {date} is sunny";
    }
}
#endregion weather_report

public partial class TypeSafeFunctionCall
{
    public async Task Consume()
    {
        #region weather_report_consume
        var functionInstance = new TypeSafeFunctionCall();

        // Get the generated function definition
        var functionDefiniton = functionInstance.WeatherReportFunctionContract.ToChatTool();

        // Get the generated function wrapper
        Func<string, Task<string>> functionWrapper = functionInstance.WeatherReportWrapper;

        // ...
        #endregion weather_report_consume
    }
}
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
    public FunctionContract WeatherReportFunctionContract
    {
        get => new FunctionContract
        {
            ClassName = @"TypeSafeFunctionCall",
            Name = @"WeatherReport",
            Description = @"Get weather report",
            ReturnType = typeof(Task<string>),
            Parameters = new global::AutoGen.Core.FunctionParameterContract[]
            {
                    new FunctionParameterContract
                    {
                        Name = @"city",
                        Description = @"city",
                        ParameterType = typeof(string),
                        IsRequired = true,
                    },
                    new FunctionParameterContract
                    {
                        Name = @"date",
                        Description = @"date",
                        ParameterType = typeof(string),
                        IsRequired = true,
                    },
            },
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
