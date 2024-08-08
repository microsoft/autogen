// Copyright (c) Microsoft Corporation. All rights reserved.
// Dynamic_Group_Chat.cs

using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using AutoGen.SemanticKernel;
using AutoGen.SemanticKernel.Extension;
using Azure.AI.OpenAI;
using Microsoft.SemanticKernel;

namespace AutoGen.BasicSample;

public class Dynamic_Group_Chat
{
    public static async Task RunAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var model = "gpt-3.5-turbo";

        #region Create_Coder
        var openaiClient = new OpenAIClient(apiKey);
        var coder = new OpenAIChatAgent(
            openAIClient: openaiClient,
            name: "coder",
            modelName: model,
            systemMessage: "You are a C# coder, when writing csharp code, please put the code between ```csharp and ```")
            .RegisterMessageConnector() // convert OpenAI message to AutoGen message
            .RegisterPrintMessage(); // print the message content
        #endregion Create_Coder

        #region Create_Commenter
        var kernel = Kernel
            .CreateBuilder()
            .AddOpenAIChatCompletion(modelId: model, apiKey: apiKey)
            .Build();
        var commenter = new SemanticKernelAgent(
            kernel: kernel,
            name: "commenter",
            systemMessage: "You write inline comments for the code snippet and add unit tests if necessary")
            .RegisterMessageConnector() // register message connector so it support AutoGen built-in message types like TextMessage.
            .RegisterPrintMessage(); // pretty print the message to the console
        #endregion Create_Commenter

        #region Create_UserProxy
        var userProxy = new DefaultReplyAgent("user", defaultReply: "END")
            .RegisterPrintMessage(); // print the message content
        #endregion Create_UserProxy

        #region Create_Group
        var admin = new OpenAIChatAgent(
            openAIClient: openaiClient,
            name: "admin",
            modelName: model)
            .RegisterMessageConnector(); // convert OpenAI message to AutoGen message

        var group = new GroupChat(
            members: [coder, commenter, userProxy],
            admin: admin);
        #endregion Create_Group

        #region Chat_With_Group
        var workflowInstruction = new TextMessage(
            Role.User,
            """
            Here is the workflow of this group chat:
            User{Ask a question} -> Coder{Write code}
            Coder{Write code} -> Commenter{Add comments to the code}
            Commenter{Add comments to the code} -> User{END}
            """);

        var question = new TextMessage(Role.User, "How to calculate the 100th Fibonacci number?");
        var chatHistory = new List<IMessage> { workflowInstruction, question };
        while (true)
        {
            var replies = await group.CallAsync(chatHistory, maxRound: 1);
            var lastReply = replies.Last();
            chatHistory.Add(lastReply);

            if (lastReply.From == userProxy.Name)
            {
                break;
            }
        }
        #endregion Chat_With_Group

        #region Summarize_Chat_History
        var summary = await coder.SendAsync("summarize the conversation", chatHistory: chatHistory);
        #endregion Summarize_Chat_History
    }
}
