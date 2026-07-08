// Copyright (c) Microsoft Corporation. All rights reserved.
// Chat_With_Agent.cs

#region Using
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
#endregion Using

using FluentAssertions;

namespace AutoGen.Basic.Sample;

public class Chat_With_Agent
{
    public static async Task RunAsync()
    {
        #region Create_Agent
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();
        var agent = new OpenAIChatAgent(
            chatClient: gpt4o,
            name: "agent",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector(); // convert OpenAI message to AutoGen message
        #endregion Create_Agent

        #region Chat_With_Agent
        var reply = await agent.SendAsync("Tell me a joke");
        reply.Should().BeOfType<TextMessage>();
        if (reply is TextMessage textMessage)
        {
            Console.WriteLine(textMessage.Content);
        }
        #endregion Chat_With_Agent

        #region Chat_With_History
        reply = await agent.SendAsync("summarize the conversation", chatHistory: [reply]);
        #endregion Chat_With_History

        #region Streaming_Chat
        var question = new TextMessage(Role.User, "Tell me a long joke");
        await foreach (var streamingReply in agent.GenerateStreamingReplyAsync([question]))
        {
            if (streamingReply is TextMessageUpdate textMessageUpdate)
            {
                Console.WriteLine(textMessageUpdate.Content);
            }
        }
        #endregion Streaming_Chat

        #region verify_reply
        reply.Should().BeOfType<TextMessage>();
        #endregion verify_reply
    }
}
