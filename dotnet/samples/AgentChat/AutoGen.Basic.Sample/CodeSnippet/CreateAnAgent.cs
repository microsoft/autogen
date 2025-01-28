// Copyright (c) Microsoft Corporation. All rights reserved.
// CreateAnAgent.cs

using AutoGen;
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using FluentAssertions;
using OpenAI;

public partial class AssistantCodeSnippet
{
    public void CodeSnippet1()
    {
        #region code_snippet_1
        // get OpenAI Key and create config
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var llmConfig = new OpenAIConfig(openAIKey, "gpt-3.5-turbo");

        // create assistant agent
        var assistantAgent = new AssistantAgent(
            name: "assistant",
            systemMessage: "You are an assistant that help user to do some tasks.",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = new[] { llmConfig },
            });
        #endregion code_snippet_1

    }

    public void CodeSnippet2()
    {
        #region code_snippet_2
        // get OpenAI Key and create config
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY");
        var model = "gpt-4o-mini";

        var openAIClient = new OpenAIClient(apiKey);

        // create assistant agent
        var assistantAgent = new OpenAIChatAgent(
            name: "assistant",
            systemMessage: "You are an assistant that help user to do some tasks.",
            chatClient: openAIClient.GetChatClient(model))
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion code_snippet_2
    }

    #region code_snippet_3
    /// <summary>
    /// convert input to upper case
    /// </summary>
    /// <param name="input">input</param>
    [Function]
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
        var model = "gpt-4o-mini";
        var openAIClient = new OpenAIClient(new System.ClientModel.ApiKeyCredential(apiKey), new OpenAIClientOptions
        {
            Endpoint = new Uri(endPoint),
        });
        #region code_snippet_4
        var assistantAgent = new OpenAIChatAgent(
            chatClient: openAIClient.GetChatClient(model),
            name: "assistant",
            systemMessage: "You are an assistant that convert user input to upper case.",
            functions: [
                this.UpperCaseFunctionContract.ToChatTool(), // The FunctionDefinition object for the UpperCase function
            ])
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        var response = await assistantAgent.SendAsync("hello");
        response.Should().BeOfType<ToolCallMessage>();
        var toolCallMessage = (ToolCallMessage)response;
        toolCallMessage.ToolCalls.Count.Should().Be(1);
        toolCallMessage.ToolCalls.First().FunctionName.Should().Be("UpperCase");
        #endregion code_snippet_4
    }

    public async Task CodeSnippet5()
    {
        // get OpenAI Key and create config
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY");
        string endPoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT"); // change to your endpoint
        var model = "gpt-4o-mini";
        var openAIClient = new OpenAIClient(new System.ClientModel.ApiKeyCredential(apiKey), new OpenAIClientOptions
        {
            Endpoint = new Uri(endPoint),
        });
        #region code_snippet_5
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [this.UpperCaseFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>()
            {
                { this.UpperCaseFunctionContract.Name, this.UpperCase },
            });
        var assistantAgent = new OpenAIChatAgent(
            name: "assistant",
            systemMessage: "You are an assistant that convert user input to upper case.",
            chatClient: openAIClient.GetChatClient(model))
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionCallMiddleware);

        var response = await assistantAgent.SendAsync("hello");
        response.Should().BeOfType<TextMessage>();
        response.From.Should().Be("assistant");
        var textMessage = (TextMessage)response;
        textMessage.Content.Should().Be("HELLO");
        #endregion code_snippet_5
    }
}
