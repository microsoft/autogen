// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAICodeSnippet.cs

#region using_statement
using AutoGen.Core;
using AutoGen.OpenAI.V1;
using AutoGen.OpenAI.V1.Extension;
using Azure.AI.OpenAI;
#endregion using_statement
using FluentAssertions;

namespace AutoGen.BasicSample.CodeSnippet;
#region weather_function
public partial class Functions
{
    [Function]
    public async Task<string> GetWeather(string location)
    {
        return "The weather in " + location + " is sunny.";
    }
}
#endregion weather_function
public partial class OpenAICodeSnippet
{
    [Function]
    public async Task<string> GetWeather(string location)
    {
        return "The weather in " + location + " is sunny.";
    }

    public async Task CreateOpenAIChatAgentAsync()
    {
        #region create_openai_chat_agent
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-3.5-turbo";
        var openAIClient = new OpenAIClient(openAIKey);

        // create an open ai chat agent
        var openAIChatAgent = new OpenAIChatAgent(
            openAIClient: openAIClient,
            name: "assistant",
            modelName: modelId,
            systemMessage: "You are an assistant that help user to do some tasks.");

        // OpenAIChatAgent supports the following message types:
        // - IMessage<ChatRequestMessage> where ChatRequestMessage is from Azure.AI.OpenAI

        var helloMessage = new ChatRequestUserMessage("Hello");

        // Use MessageEnvelope.Create to create an IMessage<ChatRequestMessage>
        var chatMessageContent = MessageEnvelope.Create(helloMessage);
        var reply = await openAIChatAgent.SendAsync(chatMessageContent);

        // The type of reply is MessageEnvelope<ChatResponseMessage> where ChatResponseMessage is from Azure.AI.OpenAI
        reply.Should().BeOfType<MessageEnvelope<ChatResponseMessage>>();

        // You can un-envelop the reply to get the ChatResponseMessage
        ChatResponseMessage response = reply.As<MessageEnvelope<ChatResponseMessage>>().Content;
        response.Role.Should().Be(ChatRole.Assistant);
        #endregion create_openai_chat_agent

        #region create_openai_chat_agent_streaming
        var streamingReply = openAIChatAgent.GenerateStreamingReplyAsync(new[] { chatMessageContent });

        await foreach (var streamingMessage in streamingReply)
        {
            streamingMessage.Should().BeOfType<MessageEnvelope<StreamingChatCompletionsUpdate>>();
            streamingMessage.As<MessageEnvelope<StreamingChatCompletionsUpdate>>().Content.Role.Should().Be(ChatRole.Assistant);
        }
        #endregion create_openai_chat_agent_streaming

        #region register_openai_chat_message_connector
        // register message connector to support more message types
        var agentWithConnector = openAIChatAgent
            .RegisterMessageConnector();

        // now the agentWithConnector supports more message types
        var messages = new IMessage[]
        {
            MessageEnvelope.Create(new ChatRequestUserMessage("Hello")),
            new TextMessage(Role.Assistant, "Hello", from: "user"),
            new MultiModalMessage(Role.Assistant,
                [
                    new TextMessage(Role.Assistant, "Hello", from: "user"),
                ],
                from: "user"),
            new TextMessage(Role.Assistant, "Hello", from: "user"), // Message type is going to be deprecated, please use TextMessage instead
        };

        foreach (var message in messages)
        {
            reply = await agentWithConnector.SendAsync(message);

            reply.Should().BeOfType<TextMessage>();
            reply.As<TextMessage>().From.Should().Be("assistant");
        }
        #endregion register_openai_chat_message_connector
    }

    public async Task OpenAIChatAgentGetWeatherFunctionCallAsync()
    {
        #region openai_chat_agent_get_weather_function_call
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelId = "gpt-3.5-turbo";
        var openAIClient = new OpenAIClient(openAIKey);

        // create an open ai chat agent
        var openAIChatAgent = new OpenAIChatAgent(
            openAIClient: openAIClient,
            name: "assistant",
            modelName: modelId,
            systemMessage: "You are an assistant that help user to do some tasks.")
            .RegisterMessageConnector();

        #endregion openai_chat_agent_get_weather_function_call

        #region create_function_call_middleware
        var functions = new Functions();
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [functions.GetWeatherFunctionContract], // GetWeatherFunctionContract is auto-generated from the GetWeather function
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { functions.GetWeatherFunctionContract.Name, functions.GetWeatherWrapper } // GetWeatherWrapper is a wrapper function for GetWeather, which is also auto-generated
            });

        openAIChatAgent = openAIChatAgent.RegisterStreamingMiddleware(functionCallMiddleware);
        #endregion create_function_call_middleware

        #region chat_agent_send_function_call
        var reply = await openAIChatAgent.SendAsync("what is the weather in Seattle?");
        reply.GetContent().Should().Be("The weather in Seattle is sunny.");
        reply.GetToolCalls().Count.Should().Be(1);
        reply.GetToolCalls().First().Should().Be(this.GetWeatherFunctionContract.Name);
        #endregion chat_agent_send_function_call
    }
}
