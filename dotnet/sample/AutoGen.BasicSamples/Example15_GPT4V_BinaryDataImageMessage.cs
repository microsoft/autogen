// Copyright (c) Microsoft Corporation. All rights reserved.
// Example15_GPT4V_BinaryDataImageMessage.cs

using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;

namespace AutoGen.BasicSample;

/// <summary>
/// This example shows usage of ImageMessage. The image is loaded as BinaryData and sent to GPT-4V 
/// <br>
/// <br>
/// Add additional images to the ImageResources to load and send more images to GPT-4V 
/// </summary>
public static class Example15_GPT4V_BinaryDataImageMessage
{
    private static readonly string ImageResourcePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "resource", "images");

    private static Dictionary<string, string> _mediaTypeMappings = new()
    {
        { ".png", "image/png" },
        { ".jpeg", "image/jpeg" },
        { ".jpg", "image/jpeg" },
        { ".gif", "image/gif" },
        { ".webp", "image/webp" }
    };

    public static async Task RunAsync()
    {
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();

        var visionAgent = new OpenAIChatAgent(
            chatClient: gpt4o,
            name: "gpt",
            systemMessage: "You are a helpful AI assistant",
            temperature: 0)
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        List<IMessage> messages =
            [new TextMessage(Role.User, "What is this image?", from: "user")];
        AddMessagesFromResource(ImageResourcePath, messages);

        var multiModalMessage = new MultiModalMessage(Role.User, messages, from: "user");
        var response = await visionAgent.SendAsync(multiModalMessage);
    }

    private static void AddMessagesFromResource(string imageResourcePath, List<IMessage> messages)
    {
        foreach (string file in Directory.GetFiles(imageResourcePath))
        {
            if (!_mediaTypeMappings.TryGetValue(Path.GetExtension(file).ToLowerInvariant(), out var mediaType))
            {
                continue;
            }

            using var fs = new FileStream(file, FileMode.Open, FileAccess.Read);
            var ms = new MemoryStream();
            fs.CopyTo(ms);
            ms.Seek(0, SeekOrigin.Begin);
            var imageData = BinaryData.FromStream(ms, mediaType);
            messages.Add(new ImageMessage(Role.Assistant, imageData, from: "user"));
        }
    }
}
