// Copyright (c) Microsoft Corporation. All rights reserved.
// CreateAnAgent.cs

using System.Text.Json;
using AutoGen;
using AutoGen.OpenAI;
using Azure.AI.OpenAI;
using FluentAssertions;

public partial class FunctionCallCodeSnippet
{
    #region code_snippet_1
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

    #region code_snippet_3
    public async Task<string> UpperCase(string input)
    {
        var result = input.ToUpper();
        return result;
    }

    #endregion code_snippet_3

    public async Task CodeSnippet4()
    {
        // get OpenAI Key and create config
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY");
        string endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT"); // change to your endpoint

        var llmConfig = new AzureOpenAIConfig(
            endpoint: endPoint,
            deploymentName: "gpt-3.5-turbo-16k", // change to your deployment name
            apiKey: apiKey);
        #region code_snippet_4
        var assistantAgent = new AssistantAgent(
            name: "assistant",
            systemMessage: "You are an assistant that convert user input to upper case.",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = new[]
                {
                    llmConfig
                },
                FunctionDefinitions = new[]
                {
                    this.UpperCaseFunction, // The FunctionDefinition object for the UpperCase function
                },
            });

        var response = await assistantAgent.SendAsync("hello");
        response.FunctionName.Should().Be("UpperCase");
        #endregion code_snippet_4
    }


    public async Task CodeSnippet5()
    {
        // get OpenAI Key and create config
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY");
        string endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT"); // change to your endpoint

        var llmConfig = new AzureOpenAIConfig(
            endpoint: endPoint,
            deploymentName: "gpt-3.5-turbo-16k", // change to your deployment name
            apiKey: apiKey);
        #region code_snippet_5
        var agent = new GPTAgent(
            name: "gpt",
            systemMessage: "You are an assistant that convert user input to upper case.",
            config: llmConfig,
            functions: new[]
            {
                this.UpperCaseFunction, // The FunctionDefinition object for the UpperCase function
            });

        #endregion code_snippet_5

        #region code_snippet_5_1
        var response = await agent.SendAsync("convert the input to upper case: hello world");
        #endregion code_snippet_5_1

        #region code_snippet_5_2
        response.FunctionName.Should().Be(nameof(UpperCase));
        response.FunctionArguments.Should().Be(@"
{{
    ""input"": ""hello world""
}}");
        #endregion code_snippet_5_2

    }

    public async Task CodeSnippet6()
    {
        // get OpenAI Key and create config
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY");
        string endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT"); // change to your endpoint

        var llmConfig = new AzureOpenAIConfig(
            endpoint: endPoint,
            deploymentName: "gpt-3.5-turbo-16k", // change to your deployment name
            apiKey: apiKey);
        #region code_snippet_6
        var assistantAgent = new AssistantAgent(
            name: "assistant",
            systemMessage: "You are an assistant that convert user input to upper case.",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = new[]
                {
                    llmConfig
                },
                FunctionDefinitions = new[]
                {
                    this.UpperCaseFunction, // The FunctionDefinition object for the UpperCase function
                },
            },
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { this.UpperCaseFunction.Name, this.UpperCaseWrapper }, // The wrapper function for the UpperCase function
            });

        #endregion code_snippet_6

        #region code_snippet_6_1
        var response = await assistantAgent.SendAsync("convert the input to upper case: hello world");
        response.Content.Should().Be("HELLO WORLD");
        #endregion code_snippet_6_1
    }
}
