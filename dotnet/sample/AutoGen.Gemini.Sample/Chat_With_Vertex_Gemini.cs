// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// Chat_With_Vertex_Gemini.cs

#region Using
using AutoGen.Core;
#endregion Using
using FluentAssertions;

namespace AutoGen.Gemini.Sample;

public class Chat_With_Vertex_Gemini
{
    public static async Task RunAsync()
    {
        #region Create_Gemini_Agent
        var projectID = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID");

        if (projectID is null)
        {
            Console.WriteLine("Please set GCP_VERTEX_PROJECT_ID environment variable.");
            return;
        }

        var geminiAgent = new GeminiChatAgent(
                name: "gemini",
                model: "gemini-1.5-flash-001",
                location: "us-east1",
                project: projectID,
                systemMessage: "You are a helpful C# engineer, put your code between ```csharp and ```, don't explain the code")
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion Create_Gemini_Agent

        #region Chat_With_Vertex_Gemini
        var reply = await geminiAgent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
        #endregion Chat_With_Vertex_Gemini

        #region verify_reply
        reply.Should().BeOfType<TextMessage>();
        #endregion verify_reply
    }
}
