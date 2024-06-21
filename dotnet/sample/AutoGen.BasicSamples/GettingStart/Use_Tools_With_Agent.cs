// Copyright (c) Microsoft Corporation. All rights reserved.
// Use_Tools_With_Agent.cs

#region Using
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;
#endregion Using
using FluentAssertions;

namespace AutoGen.BasicSample;

public partial class Tools
{
    /// <summary>
    /// Get the weather of the city.
    /// </summary>
    /// <param name="city"></param>
    [Function]
    public async Task<string> GetWeather(string city)
    {
        return $"The weather in {city} is sunny.";
    }
}
public class Use_Tools_With_Agent
{
    public static async Task RunAsync()
    {
        #region Create_tools
        var tools = new Tools();
        #endregion Create_tools

        #region Create_Agent
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var model = "gpt-3.5-turbo";
        var openaiClient = new OpenAIClient(apiKey);
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [tools.GetWeatherFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>()
            {
                { tools.GetWeatherFunctionContract.Name!, tools.GetWeatherWrapper },
            });
        var agent = new OpenAIChatAgent(
            openAIClient: openaiClient,
            name: "agent",
            modelName: model,
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector() // convert OpenAI message to AutoGen message
            .RegisterMiddleware(functionCallMiddleware) // pass function definition to agent.
            .RegisterPrintMessage(); // print the message content
        #endregion Create_Agent

        #region Single_Turn_Tool_Call
        var question = new TextMessage(Role.User, "What is the weather in Seattle?");
        var toolCallReply = await agent.SendAsync(question);
        #endregion Single_Turn_Tool_Call

        #region verify_too_call_reply
        toolCallReply.Should().BeOfType<ToolCallAggregateMessage>();
        #endregion verify_too_call_reply

        #region Multi_Turn_Tool_Call
        var finalReply = await agent.SendAsync(chatHistory: [question, toolCallReply]);
        #endregion Multi_Turn_Tool_Call

        #region verify_reply
        finalReply.Should().BeOfType<TextMessage>();
        #endregion verify_reply

        #region parallel_tool_call
        question = new TextMessage(Role.User, "What is the weather in Seattle, New York and Vancouver");
        toolCallReply = await agent.SendAsync(question);
        #endregion parallel_tool_call

        #region verify_parallel_tool_call_reply
        toolCallReply.Should().BeOfType<ToolCallAggregateMessage>();
        (toolCallReply as ToolCallAggregateMessage)!.Message1.ToolCalls.Count().Should().Be(3);
        #endregion verify_parallel_tool_call_reply

        #region Multi_Turn_Parallel_Tool_Call
        finalReply = await agent.SendAsync(chatHistory: [question, toolCallReply]);
        #endregion Multi_Turn_Parallel_Tool_Call
    }
}
