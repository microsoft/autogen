// Copyright (c) Microsoft Corporation. All rights reserved.
// Example09_SemanticKernel.cs

using System.ComponentModel;
using AutoGen.SemanticKernel.Extension;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
namespace AutoGen.BasicSample;

public class LightPlugin
{
    public bool IsOn { get; set; } = false;

    [KernelFunction]
    [Description("Gets the state of the light.")]
    public string GetState() => this.IsOn ? "on" : "off";

    [KernelFunction]
    [Description("Changes the state of the light.'")]
    public string ChangeState(bool newState)
    {
        this.IsOn = newState;
        var state = this.GetState();

        // Print the state to the console
        Console.ForegroundColor = ConsoleColor.DarkBlue;
        Console.WriteLine($"[Light is now {state}]");
        Console.ResetColor();

        return state;
    }
}

public class Example09_SemanticKernel
{
    public static async Task RunAsync()
    {
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-3.5-turbo";
        var builder = Kernel.CreateBuilder()
            .AddOpenAIChatCompletion(modelId: modelId, apiKey: openAIKey);
        var kernel = builder.Build();
        var settings = new OpenAIPromptExecutionSettings
        {
            ToolCallBehavior = ToolCallBehavior.AutoInvokeKernelFunctions,
        };

        kernel.Plugins.AddFromObject(new LightPlugin());
        var assistantAgent = kernel
            .ToSemanticKernelAgent(name: "assistant", systemMessage: "You control the light", settings)
            .RegisterPrintFormatMessageHook();


        var userProxyAgent = new UserProxyAgent(name: "user", humanInputMode: ConversableAgent.HumanInputMode.ALWAYS);
        await userProxyAgent.InitiateChatAsync(
            receiver: assistantAgent,
            message: "Hey assistant, please help me to do some tasks.",
            maxRound: 10);
    }

}
