// Copyright (c) Microsoft Corporation. All rights reserved.
// Use_Kernel_Functions_With_Other_Agent.cs

#region Using
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using Microsoft.SemanticKernel;
using OpenAI;
#endregion Using

namespace AutoGen.SemanticKernel.Sample;

public class Use_Kernel_Functions_With_Other_Agent
{
    public static async Task RunAsync()
    {
        #region Create_plugin
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-4o-mini";
        var kernelBuilder = Kernel.CreateBuilder();
        var kernel = kernelBuilder.Build();
        var getWeatherFunction = KernelFunctionFactory.CreateFromMethod(
                       method: (string location) => $"The weather in {location} is 75 degrees Fahrenheit.",
                       functionName: "GetWeather",
                       description: "Get the weather for a location.");
        var plugin = kernel.CreatePluginFromFunctions("my_plugin", [getWeatherFunction]);
        #endregion Create_plugin

        #region Use_plugin
        // Create a middleware to handle the plugin functions
        var kernelPluginMiddleware = new KernelPluginMiddleware(kernel, plugin);

        var openAIClient = new OpenAIClient(openAIKey);
        var openAIAgent = new OpenAIChatAgent(
            chatClient: openAIClient.GetChatClient(modelId),
            name: "assistant")
            .RegisterMessageConnector() // register message connector so it support AutoGen built-in message types like TextMessage.
            .RegisterMiddleware(kernelPluginMiddleware) // register the middleware to handle the plugin functions
            .RegisterPrintMessage(); // pretty print the message to the console
        #endregion Use_plugin

        #region Send_message
        var toolAggregateMessage = await openAIAgent.SendAsync("Tell me the weather in Seattle");

        // The aggregate message will be converted to [ToolCallMessage, ToolCallResultMessage] when flowing into the agent
        // send the aggregated message to llm to generate the final response
        var finalReply = await openAIAgent.SendAsync(toolAggregateMessage);
        #endregion Send_message
    }
}
