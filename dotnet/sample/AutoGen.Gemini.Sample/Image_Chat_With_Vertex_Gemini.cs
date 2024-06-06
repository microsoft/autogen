// Copyright (c) Microsoft Corporation. All rights reserved.
// Image_Chat_With_Vertex_Gemini.cs

using AutoGen.Core;
using AutoGen.Gemini.Middleware;

namespace AutoGen.Gemini.Sample;

public class Image_Chat_With_Vertex_Gemini
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
            systemMessage: "You explain image content to user")
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion Create_Gemini_Agent

        #region Send_Image_Request
        var imagePath = Path.Combine("resource", "images", "background.png");
        var image = File.ReadAllBytes(imagePath);
        var imageMessage = new ImageMessage(Role.User, BinaryData.FromBytes(image, "image/png"));
        await geminiAgent.SendAsync("what's in the image", [imageMessage]);
        #endregion Send_Image_Request
    }
}
