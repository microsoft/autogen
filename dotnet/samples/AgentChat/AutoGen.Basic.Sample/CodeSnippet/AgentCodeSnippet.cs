// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentCodeSnippet.cs

using AutoGen.Core;

namespace AutoGen.Basic.Sample.CodeSnippet;

internal class AgentCodeSnippet
{
    public async Task ChatWithAnAgent(IStreamingAgent agent)
    {
        #region ChatWithAnAgent_GenerateReplyAsync
        var message = new TextMessage(Role.User, "Hello");
        IMessage reply = await agent.GenerateReplyAsync([message]);
        #endregion ChatWithAnAgent_GenerateReplyAsync

        #region ChatWithAnAgent_SendAsync
        reply = await agent.SendAsync("Hello");
        #endregion ChatWithAnAgent_SendAsync

        #region ChatWithAnAgent_GenerateStreamingReplyAsync
        var textMessage = new TextMessage(Role.User, "Hello");
        await foreach (var streamingReply in agent.GenerateStreamingReplyAsync([message]))
        {
            if (streamingReply is TextMessageUpdate update)
            {
                Console.Write(update.Content);
            }
        }
        #endregion ChatWithAnAgent_GenerateStreamingReplyAsync
    }
}
