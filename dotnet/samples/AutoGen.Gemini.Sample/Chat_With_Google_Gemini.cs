// Copyright (c) Microsoft Corporation. All rights reserved.
// Chat_With_Google_Gemini.cs

#region Using
using AutoGen.Core;
#endregion Using
using FluentAssertions;

namespace AutoGen.Gemini.Sample;

public class Chat_With_Google_Gemini
{
    public static async Task RunAsync()
    {
        #region Create_Gemini_Agent
        var apiKey = Environment.GetEnvironmentVariable("GOOGLE_GEMINI_API_KEY");

        if (apiKey is null)
        {
            Console.WriteLine("Please set GOOGLE_GEMINI_API_KEY environment variable.");
            return;
        }

        var geminiAgent = new GeminiChatAgent(
                name: "gemini",
                model: "gemini-1.5-flash-001",
                apiKey: apiKey,
                systemMessage: "You are a helpful C# engineer, put your code between ```csharp and ```, don't explain the code")
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion Create_Gemini_Agent

        #region Chat_With_Google_Gemini
        var reply = await geminiAgent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
        #endregion Chat_With_Google_Gemini

        #region verify_reply
        reply.Should().BeOfType<TextMessage>();
        #endregion verify_reply
    }
}
