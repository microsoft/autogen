// Copyright (c) Microsoft Corporation. All rights reserved.
// Example03_Agent_FunctionCall.cs

using AutoGen;
using FluentAssertions;
using autogen = AutoGen.LLMConfigAPI;

/// <summary>
/// This example shows how to add type-safe function call to an agent.
/// </summary>
public partial class Example03_Agent_FunctionCall
{
    /// <summary>
    /// upper case the message when asked.
    /// </summary>
    /// <param name="message"></param>
    [Function]
    public async Task<string> UpperCase(string message)
    {
        return message.ToUpper();
    }

    /// <summary>
    /// Concatenate strings.
    /// </summary>
    /// <param name="strings">strings to concatenate</param>
    [Function]
    public async Task<string> ConcatString(string[] strings)
    {
        return string.Join(" ", strings);
    }

    /// <summary>
    /// calculate tax
    /// </summary>
    /// <param name="price">price, should be an integer</param>
    /// <param name="taxRate">tax rate, should be in range (0, 1)</param>
    [FunctionAttribute]
    public async Task<string> CalculateTax(int price, float taxRate)
    {
        return $"tax is {price * taxRate}";
    }

    public async Task RunAsync()
    {
        // get OpenAI Key and create config
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var llmConfig = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-3.5-turbo" }); // the version of GPT needs to support function call, a.k.a later than 0613

        // AutoGen makes use of AutoGen.SourceGenerator to automatically generate FunctionDefinition and FunctionCallWrapper for you.
        // The FunctionDefinition will be created based on function signature and XML documentation.
        // The return type of type-safe function needs to be Task<string>. And to get the best performance, please try only use primitive types and arrays of primitive types as parameters.
        var config = new ConversableAgentConfig
        {
            Temperature = 0,
            ConfigList = llmConfig,
            FunctionContracts = new[]
            {
                ConcatStringFunctionContract,
                UpperCaseFunctionContract,
                CalculateTaxFunctionContract,
            },
        };

        var agent = new AssistantAgent(
            name: "agent",
            systemMessage: "You are a helpful AI assistant",
            llmConfig: config,
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { nameof(ConcatString), this.ConcatStringWrapper },
                { nameof(UpperCase), this.UpperCaseWrapper },
                { nameof(CalculateTax), this.CalculateTaxWrapper },
            })
            .RegisterPrintFormatMessageHook();

        // talk to the assistant agent
        var upperCase = await agent.SendAsync("convert to upper case: hello world");
        upperCase.Should().BeOfType<AggregateMessage<ToolCallMessage, ToolCallResultMessage>>();
        upperCase.GetContent()?.Should().Be("HELLO WORLD");

        var concatString = await agent.SendAsync("concatenate strings: a, b, c, d, e");
        concatString.Should().BeOfType<AggregateMessage<ToolCallMessage, ToolCallResultMessage>>();
        concatString.GetContent()?.Should().Be("a b c d e");

        var calculateTax = await agent.SendAsync("calculate tax: 100, 0.1");
        calculateTax.Should().BeOfType<AggregateMessage<ToolCallMessage, ToolCallResultMessage>>();
        calculateTax.GetContent().Should().Be("tax is 10");
    }
}
