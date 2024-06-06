// Copyright (c) Microsoft Corporation. All rights reserved.
// Chat_With_Vertex_Gemini.cs

using AutoGen.Core;
using AutoGen.Gemini.Middleware;

namespace AutoGen.Gemini.Sample;

public class Chat_With_Vertex_Gemini
{
    public static async Task RunAsync()
    {
        var projectID = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID");

        if (projectID is null)
        {
            Console.WriteLine("Please set GCP_VERTEX_PROJECT_ID environment variable.");
            return;
        }
        #region Create_Gemini_Agent
        var geminiAgent = new GeminiChatAgent(
                name: "gemini",
                model: "gemini-1.5-flash-001",
                location: "us-central1",
                project: projectID,
                systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        await geminiAgent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
        #endregion Create_Gemini_Agent
    }
}
