// Copyright (c) Microsoft Corporation. All rights reserved.
// Create_Ollama_Agent_With_Tool.cs

using AutoGen.Core;
using AutoGen.Ollama.Extension;
using FluentAssertions;

namespace AutoGen.Ollama.Sample;

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

public class Create_Ollama_Agent_With_Tool
{
    public static async Task RunAsync()
    {
        #region define_tool
        var tool = new Tool()
        {
            Function = new Function
            {
                Name = "get_current_weather",
                Description = "Get the current weather for a location",
                Parameters = new Parameters
                {
                    Properties = new Dictionary<string, Properties>
                    {
                        {
                            "location",
                            new Properties
                            {
                                Type = "string", Description = "The location to get the weather for, e.g. San Francisco, CA"
                            }
                        },
                        {
                            "format", new Properties
                            {
                                Type = "string",
                                Description =
                                    "The format to return the weather in, e.g. 'celsius' or 'fahrenheit'",
                                Enum = new List<string> {"celsius", "fahrenheit"}
                            }
                        }
                    },
                    Required = new List<string> { "location", "format" }
                }
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

        #region create_ollama_agent_llama3.1

        var agent = new OllamaAgent(
            new HttpClient { BaseAddress = new Uri("http://localhost:11434") },
            "MyAgent",
            "llama3.1",
            tools: [tool]);
        #endregion

        // TODO cannot stream
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
