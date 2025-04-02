This tutorial shows how to perform image chat with an agent using the @AutoGen.OpenAI.OpenAIChatAgent as an example.

> [!NOTE]
> To chat image with an agent, the model behind the agent needs to support image input. Here is a partial list of models that support image input:
> - gpt-4o
> - gemini-1.5
> - llava
> - claude-3
> - ...
>
> In this example, we are using the gpt-4o model as the backend model for the agent.

> [!NOTE]
> The complete code example can be found in [Image_Chat_With_Agent.cs](https://github.com/microsoft/autogen/blob/main/dotnet/samples/AgentChat/Autogen.Basic.Sample/GettingStart/Image_Chat_With_Agent.cs)

## Step 1: Install AutoGen

First, install the AutoGen package using the following command:

```bash
dotnet add package AutoGen
```

## Step 2: Add Using Statements

[!code-csharp[Using Statements](../../samples/AgentChat/Autogen.Basic.Sample/GettingStart/Image_Chat_With_Agent.cs?name=Using)]

## Step 3: Create an @AutoGen.OpenAI.OpenAIChatAgent

[!code-csharp[Create an OpenAIChatAgent](../../samples/AgentChat/Autogen.Basic.Sample/GettingStart/Image_Chat_With_Agent.cs?name=Create_Agent)]

## Step 4: Prepare Image Message

In AutoGen, you can create an image message using either @AutoGen.Core.ImageMessage or @AutoGen.Core.MultiModalMessage. The @AutoGen.Core.ImageMessage takes a single image as input, whereas the @AutoGen.Core.MultiModalMessage allows you to pass multiple modalities like text or image.

Here is how to create an image message using @AutoGen.Core.ImageMessage:
[!code-csharp[Create Image Message](../../samples/AgentChat/Autogen.Basic.Sample/GettingStart/Image_Chat_With_Agent.cs?name=Prepare_Image_Input)]

Here is how to create a multimodal message using @AutoGen.Core.MultiModalMessage:
[!code-csharp[Create MultiModal Message](../../samples/AgentChat/Autogen.Basic.Sample/GettingStart/Image_Chat_With_Agent.cs?name=Prepare_Multimodal_Input)]

## Step 5: Generate Response

To generate response, you can use one of the overloaded methods of @AutoGen.Core.AgentExtension.SendAsync* method. The following code shows how to generate response with an image message:

[!code-csharp[Generate Response](../../samples/AgentChat/Autogen.Basic.Sample/GettingStart/Image_Chat_With_Agent.cs?name=Chat_With_Agent)]

## Further Reading
- [Image chat with gemini](../articles/AutoGen.Gemini/Image-chat-with-gemini.md)
- [Image chat with llava](../articles/AutoGen.Ollama/Chat-with-llava.md)