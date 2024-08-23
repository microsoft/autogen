// Copyright (c) Microsoft Corporation. All rights reserved.
// Example09_LMStudio_FunctionCall.cs

using System.Text.Json;
using System.Text.Json.Serialization;
using AutoGen.Core;
using AutoGen.LMStudio;
using AutoGen.OpenAI.V1.Extension;
using Azure.AI.OpenAI;

namespace AutoGen.BasicSample;

public class LLaMAFunctionCall
{
    [JsonPropertyName("name")]
    public string Name { get; set; }

    [JsonPropertyName("arguments")]
    public JsonElement Arguments { get; set; }
}

public partial class Example09_LMStudio_FunctionCall
{
    /// <summary>
    /// Get weather from location.
    /// </summary>
    /// <param name="location">location</param>
    /// <param name="date">date. type is string</param>
    [Function]
    public async Task<string> GetWeather(string location, string date)
    {
        return $"[Function] The weather on {date} in {location} is sunny.";
    }


    /// <summary>
    /// Search query on Google and return the results.
    /// </summary>
    /// <param name="query">search query</param>
    [Function]
    public async Task<string> GoogleSearch(string query)
    {
        return $"[Function] Here are the search results for {query}.";
    }

    private static object SerializeFunctionDefinition(FunctionDefinition functionDefinition)
    {
        return new
        {
            type = "function",
            function = new
            {
                name = functionDefinition.Name,
                description = functionDefinition.Description,
                parameters = functionDefinition.Parameters.ToObjectFromJson<object>(),
            }
        };
    }

    public static async Task RunAsync()
    {
        #region lmstudio_function_call_example
        // This example has been verified to work with Trelis-Llama-2-7b-chat-hf-function-calling-v3
        var instance = new Example09_LMStudio_FunctionCall();
        var config = new LMStudioConfig("localhost", 1234);
        var systemMessage = @$"You are a helpful AI assistant.";

        // Because the LM studio server doesn't support openai function call yet
        // To simulate the function call, we can put the function call details in the system message
        // And ask agent to response in function call object format using few-shot example
        object[] functionList =
            [
                SerializeFunctionDefinition(instance.GetWeatherFunctionContract.ToOpenAIFunctionDefinition()),
                SerializeFunctionDefinition(instance.GetWeatherFunctionContract.ToOpenAIFunctionDefinition())
            ];
        var functionListString = JsonSerializer.Serialize(functionList, new JsonSerializerOptions { WriteIndented = true });
        var lmAgent = new LMStudioAgent(
            name: "assistant",
            systemMessage: @$"
You are a helpful AI assistant
You have access to the following functions. Use them if required:

{functionListString}",
            config: config)
            .RegisterMiddleware(async (msgs, option, innerAgent, ct) =>
            {
                // inject few-shot example to the message
                var exampleGetWeather = new TextMessage(Role.User, "Get weather in London");
                var exampleAnswer = new TextMessage(Role.Assistant, "{\n    \"name\": \"GetWeather\",\n    \"arguments\": {\n        \"city\": \"London\"\n    }\n}", from: innerAgent.Name);

                msgs = new[] { exampleGetWeather, exampleAnswer }.Concat(msgs).ToArray();
                var reply = await innerAgent.GenerateReplyAsync(msgs, option, ct);

                // if reply is a function call, invoke function
                var content = reply.GetContent();
                try
                {
                    if (JsonSerializer.Deserialize<LLaMAFunctionCall>(content) is { } functionCall)
                    {
                        var arguments = JsonSerializer.Serialize(functionCall.Arguments);
                        // invoke function wrapper
                        if (functionCall.Name == instance.GetWeatherFunctionContract.Name)
                        {
                            var result = await instance.GetWeatherWrapper(arguments);
                            return new TextMessage(Role.Assistant, result);
                        }
                        else if (functionCall.Name == instance.GetWeatherFunctionContract.Name)
                        {
                            var result = await instance.GoogleSearchWrapper(arguments);
                            return new TextMessage(Role.Assistant, result);
                        }
                        else
                        {
                            throw new Exception($"Unknown function call: {functionCall.Name}");
                        }
                    }
                }
                catch (JsonException)
                {
                    // ignore
                }

                return reply;
            })
            .RegisterPrintMessage();

        var userProxyAgent = new UserProxyAgent(
            name: "user",
            humanInputMode: HumanInputMode.ALWAYS);

        await userProxyAgent.SendAsync(
            receiver: lmAgent,
            "Search the names of the five largest stocks in the US by market cap ")
            .ToArrayAsync();
        #endregion lmstudio_function_call_example
    }
}
