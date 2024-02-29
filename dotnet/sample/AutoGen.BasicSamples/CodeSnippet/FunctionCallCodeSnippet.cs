// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionCallCodeSnippet.cs

using AutoGen;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using FluentAssertions;

public partial class FunctionCallCodeSnippet
{
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
        var function = new TypeSafeFunctionCall();
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
                    function.WeatherReportFunctionContract.ToOpenAIFunctionDefinition(), // The FunctionDefinition object for the weather report function
                },
            });

        var response = await assistantAgent.SendAsync("hello What's the weather in Seattle today? today is 2024-01-01");
        response.Should().BeOfType<ToolCallMessage>();
        var toolCallMessage = (ToolCallMessage)response;
        toolCallMessage.ToolCalls.Count().Should().Be(1);
        toolCallMessage.ToolCalls[0].FunctionName.Should().Be("WeatherReport");
        toolCallMessage.ToolCalls[0].FunctionArguments.Should().Be(@"{""location"":""Seattle"",""date"":""2024-01-01""}");
        #endregion code_snippet_4
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
        var function = new TypeSafeFunctionCall();
        var assistantAgent = new AssistantAgent(
            name: "assistant",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = new[]
                {
                    llmConfig
                },
                FunctionDefinitions = new[]
                {
                    function.WeatherReportFunctionContract.ToOpenAIFunctionDefinition(), // The FunctionDefinition object for the weather report function
                },
            },
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { function.WeatherReportFunctionContract.Name, function.WeatherReportWrapper }, // The function wrapper for the weather report function
            });

        #endregion code_snippet_6

        #region code_snippet_6_1
        var response = await assistantAgent.SendAsync("What's the weather in Seattle today? today is 2024-01-01");
        response.Should().BeOfType<TextMessage>();
        var textMessage = (TextMessage)response;
        textMessage.Content.Should().Be("Weather report for Seattle on 2024-01-01 is sunny");
        #endregion code_snippet_6_1
    }

    public async Task TwoAgentWeatherChatTestAsync()
    {
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
        var deploymentName = "gpt-35-turbo-16k";
        var config = new AzureOpenAIConfig(endpoint, deploymentName, key);
        #region two_agent_weather_chat
        var function = new TypeSafeFunctionCall();
        var assistant = new AssistantAgent(
            "assistant",
            llmConfig: new ConversableAgentConfig
            {
                ConfigList = new[] { config },
                FunctionDefinitions = new[]
                {
                    function.WeatherReportFunctionContract.ToOpenAIFunctionDefinition(),
                },
            });

        var user = new UserProxyAgent(
            name: "user",
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { function.WeatherReportFunctionContract.Name, function.WeatherReportWrapper },
            });

        await user.InitiateChatAsync(assistant, "what's weather in Seattle today, today is 2024-01-01", 10);
        #endregion two_agent_weather_chat
    }
}
