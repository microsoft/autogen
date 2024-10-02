// Copyright (c) Microsoft Corporation. All rights reserved.
// Image_Chat_With_Agent.cs

#region Using
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
#endregion Using
using FluentAssertions;

namespace AutoGen.BasicSample;

public class Image_Chat_With_Agent
{
    public static async Task RunAsync()
    {
        #region Create_Agent
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();
        var agent = new OpenAIChatAgent(
            chatClient: gpt4o,
            name: "agent",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector() // convert OpenAI message to AutoGen message
            .RegisterPrintMessage();
        #endregion Create_Agent

        #region Prepare_Image_Input
        var backgoundImagePath = Path.Combine("resource", "images", "background.png");
        var imageBytes = File.ReadAllBytes(backgoundImagePath);
        var imageMessage = new ImageMessage(Role.User, BinaryData.FromBytes(imageBytes, "image/png"));
        #endregion Prepare_Image_Input

        #region Prepare_Multimodal_Input
        var textMessage = new TextMessage(Role.User, "what's in the picture");
        var multimodalMessage = new MultiModalMessage(Role.User, [textMessage, imageMessage]);
        #endregion Prepare_Multimodal_Input

        #region Chat_With_Agent
        var reply = await agent.SendAsync("what's in the picture", chatHistory: [imageMessage]);
        // or use multimodal message to generate reply
        reply = await agent.SendAsync(multimodalMessage);
        #endregion Chat_With_Agent

        #region verify_reply
        reply.Should().BeOfType<TextMessage>();
        #endregion verify_reply
    }
}
