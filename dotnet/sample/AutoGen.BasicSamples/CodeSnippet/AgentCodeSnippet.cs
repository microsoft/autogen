// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentCodeSnippet.cs
using AutoGen.Core;

namespace AutoGen.BasicSample.CodeSnippet;

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
