// Copyright (c) Microsoft Corporation. All rights reserved.
// Create_Anthropic_Agent_With_Tool.cs

using AutoGen.Anthropic.DTO;
using AutoGen.Anthropic.Extensions;
using AutoGen.Anthropic.Utils;
using AutoGen.Core;
using FluentAssertions;

namespace AutoGen.Anthropic.Sample;

#region WeatherFunction

public partial class WeatherFunction
{
    /// <summary>
    /// Gets the weather based on the location and the unit
    /// </summary>
    /// <param name="location"></param>
    /// <param name="unit"></param>
    /// <returns></returns>
    [Function]
    public async Task<string> GetWeather(string location, string unit)
    {
        // dummy implementation
        return $"The weather in {location} is currently sunny with a tempature of {unit} (s)";
    }
}
#endregion
public class Create_Anthropic_Agent_With_Tool
{
    public static async Task RunAsync()
    {
        #region define_tool
        var tool = new Tool
        {
            Name = "GetWeather",
            Description = "Get the current weather in a given location",
            InputSchema = new InputSchema
            {
                Type = "object",
                Properties = new Dictionary<string, SchemaProperty>
                {
                    { "location", new SchemaProperty { Type = "string", Description = "The city and state, e.g. San Francisco, CA" } },
                    { "unit", new SchemaProperty { Type = "string", Description = "The unit of temperature, either \"celsius\" or \"fahrenheit\"" } }
                },
                Required = new List<string> { "location" }
            }
        };

        var weatherFunction = new WeatherFunction();
        var functionMiddleware = new FunctionCallMiddleware(
            functions: [
                weatherFunction.GetWeatherFunctionContract,
            ],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { weatherFunction.GetWeatherFunctionContract.Name!, weatherFunction.GetWeatherWrapper },
            });

        #endregion

        #region create_anthropic_agent

        var apiKey = Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY") ??
                     throw new Exception("Missing ANTHROPIC_API_KEY environment variable.");

        var anthropicClient = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, apiKey);
        var agent = new AnthropicClientAgent(anthropicClient, "assistant", AnthropicConstants.Claude3Haiku,
            tools: [tool]); // Define tools for AnthropicClientAgent
        #endregion

        #region register_middleware

        var agentWithConnector = agent
            .RegisterMessageConnector()
            .RegisterPrintMessage()
            .RegisterStreamingMiddleware(functionMiddleware);
        #endregion register_middleware

        #region single_turn
        var question = new TextMessage(Role.Assistant,
            "What is the weather like in San Francisco?",
            from: "user");
        var functionCallReply = await agentWithConnector.SendAsync(question);
        #endregion

        #region Single_turn_verify_reply
        functionCallReply.Should().BeOfType<ToolCallAggregateMessage>();
        #endregion Single_turn_verify_reply

        #region Multi_turn
        var finalReply = await agentWithConnector.SendAsync(chatHistory: [question, functionCallReply]);
        #endregion Multi_turn

        #region Multi_turn_verify_reply
        finalReply.Should().BeOfType<TextMessage>();
        #endregion Multi_turn_verify_reply
    }
}
