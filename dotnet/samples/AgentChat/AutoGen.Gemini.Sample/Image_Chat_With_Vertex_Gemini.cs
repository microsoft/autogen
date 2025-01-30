// Copyright (c) Microsoft Corporation. All rights reserved.
// Image_Chat_With_Vertex_Gemini.cs

#region Using
using AutoGen.Core;
#endregion Using
using FluentAssertions;

namespace AutoGen.Gemini.Sample;

public class Image_Chat_With_Vertex_Gemini
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
            location: "us-east4",
            project: projectID,
            systemMessage: "You explain image content to user")
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion Create_Gemini_Agent

        #region Send_Image_Request
        var imagePath = Path.Combine("resource", "images", "background.png");
        var image = await File.ReadAllBytesAsync(imagePath);
        var imageMessage = new ImageMessage(Role.User, BinaryData.FromBytes(image, "image/png"));
        var reply = await geminiAgent.SendAsync("what's in the image", [imageMessage]);
        #endregion Send_Image_Request

        #region Verify_Reply
        reply.Should().BeOfType<TextMessage>();
        #endregion Verify_Reply
    }
}
