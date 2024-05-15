// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralAICodeSnippet.cs

#region using_statement
using AutoGen.Core;
using AutoGen.Mistral;
using AutoGen.Mistral.Extension;
using FluentAssertions;
#endregion using_statement

namespace AutoGen.BasicSample.CodeSnippet;

#region weather_function
public partial class MistralAgentFunction
{
    [Function]
    public async Task<string> GetWeather(string location)
    {
        return "The weather in " + location + " is sunny.";
    }
}
#endregion weather_function

internal class MistralAICodeSnippet
{
    public async Task CreateMistralAIClientAsync()
    {
        #region create_mistral_agent
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new Exception("Missing MISTRAL_API_KEY environment variable");
        var client = new MistralClient(apiKey: apiKey);
        var agent = new MistralClientAgent(
            client: client,
            name: "MistralAI",
            model: MistralAIModelID.OPEN_MISTRAL_7B)
            .RegisterMessageConnector(); // support more AutoGen built-in message types.

        await agent.SendAsync("Hello, how are you?");
        #endregion create_mistral_agent

        #region streaming_chat
        var reply = agent.GenerateStreamingReplyAsync(
            messages: [new TextMessage(Role.User, "Hello, how are you?")]
        );

        await foreach (var message in reply)
        {
            if (message is TextMessageUpdate textMessageUpdate && textMessageUpdate.Content is string content)
            {
                Console.WriteLine(content);
            }
        }
        #endregion streaming_chat
    }

    public async Task MistralAIChatAgentGetWeatherToolUsageAsync()
    {
        #region create_mistral_function_call_agent
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new Exception("Missing MISTRAL_API_KEY environment variable");
        var client = new MistralClient(apiKey: apiKey);
        var agent = new MistralClientAgent(
            client: client,
            name: "MistralAI",
            model: MistralAIModelID.MISTRAL_SMALL_LATEST)
            .RegisterMessageConnector(); // support more AutoGen built-in message types like ToolCallMessage and ToolCallResultMessage
        #endregion create_mistral_function_call_agent

        #region create_get_weather_function_call_middleware
        var mistralFunctions = new MistralAgentFunction();
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [mistralFunctions.GetWeatherFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>> // with functionMap, the function will be automatically triggered if the tool name matches one of the keys.
            {
                { mistralFunctions.GetWeatherFunctionContract.Name, mistralFunctions.GetWeather }
            });
        #endregion create_get_weather_function_call_middleware

        #region register_function_call_middleware
        agent = agent.RegisterStreamingMiddleware(functionCallMiddleware);
        #endregion register_function_call_middleware

        #region send_message_with_function_call
        var reply = await agent.SendAsync("What is the weather in Seattle?");
        reply.GetContent().Should().Be("The weather in Seattle is sunny.");
        #endregion send_message_with_function_call
    }
}
