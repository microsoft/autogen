// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// BuildInMessageCodeSnippet.cs

using AutoGen.Core;
namespace AutoGen.BasicSample.CodeSnippet;

internal class BuildInMessageCodeSnippet
{
    public async Task StreamingCallCodeSnippetAsync()
    {
        IStreamingAgent agent = default;
        #region StreamingCallCodeSnippet
        var helloTextMessage = new TextMessage(Role.User, "Hello");
        var reply = agent.GenerateStreamingReplyAsync([helloTextMessage]);
        var finalTextMessage = new TextMessage(Role.Assistant, string.Empty, from: agent.Name);
        await foreach (var message in reply)
        {
            if (message is TextMessageUpdate textMessage)
            {
                Console.Write(textMessage.Content);
                finalTextMessage.Update(textMessage);
            }
        }
        #endregion StreamingCallCodeSnippet

        #region StreamingCallWithFinalMessage
        reply = agent.GenerateStreamingReplyAsync([helloTextMessage]);
        TextMessage finalMessage = null;
        await foreach (var message in reply)
        {
            if (message is TextMessageUpdate textMessage)
            {
                Console.Write(textMessage.Content);
            }
            else if (message is TextMessage txtMessage)
            {
                finalMessage = txtMessage;
            }
        }
        #endregion StreamingCallWithFinalMessage
    }
}
