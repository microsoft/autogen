// Copyright (c) Microsoft Corporation. All rights reserved.
// Chat_With_LLaVA.cs

#region Using
using AutoGen.Core;
using AutoGen.Ollama.Extension;
#endregion Using

namespace AutoGen.Ollama.Sample;

public class Chat_With_LLaVA
{
    public static async Task RunAsync()
    {
        #region Create_Ollama_Agent
        using var httpClient = new HttpClient()
        {
            BaseAddress = new Uri("http://localhost:11434"),
        };

        var ollamaAgent = new OllamaAgent(
            httpClient: httpClient,
            name: "ollama",
            modelName: "llava:latest",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion Create_Ollama_Agent

        #region Send_Message
        var image = Path.Combine("images", "background.png");
        var binaryData = BinaryData.FromBytes(File.ReadAllBytes(image), "image/png");
        var imageMessage = new ImageMessage(Role.User, binaryData);
        var textMessage = new TextMessage(Role.User, "what's in this image?");
        var reply = await ollamaAgent.SendAsync(chatHistory: [textMessage, imageMessage]);
        #endregion Send_Message

        #region Send_MultiModal_Message
        // You can also use MultiModalMessage to put text and image together in one message
        // In this case, all the messages in the multi-modal message will be put into single piece of message
        // where the text is the concatenation of all the text messages seperated by \n
        // and the images are all the images in the multi-modal message
        var multiModalMessage = new MultiModalMessage(Role.User, [textMessage, imageMessage]);

        reply = await ollamaAgent.SendAsync(chatHistory: [multiModalMessage]);
        #endregion Send_MultiModal_Message
    }
}
