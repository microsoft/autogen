This example shows how to use @AutoGen.Gemini.GeminiChatAgent to connect to Google AI Gemini and chat with Gemini model.

To run this example, you need to have a Google AI Gemini API key. For how to get a Google Gemini API key, please refer to [Google Gemini](https://gemini.google.com/).

> [!NOTE]
> You can find the complete sample code [here](https://github.com/microsoft/autogen/blob/main/dotnet/samples/AutoGen.Gemini.Sample/Chat_With_Google_Gemini.cs)

> [!NOTE]
> What's the difference between Google AI Gemini and Vertex AI Gemini?
>
> Gemini is a series of large language models developed by Google. You can use it either from Google AI API or Vertex AI API. If you are relatively new to Gemini and wants to explore the feature and build some prototype for your chatbot app, Google AI APIs (with Google AI Studio) is a fast way to get started. While your app and idea matures and you'd like to leverage more MLOps tools that streamline the usage, deployment, and monitoring of models, you can move to Google Cloud Vertex AI which provides Gemini APIs along with many other features. Basically, to help you productionize your app. ([reference](https://stackoverflow.com/questions/78007243/utilizing-gemini-through-vertex-ai-or-through-google-generative-ai))

### Step 1: Install AutoGen.Gemini

First, install the AutoGen.Gemini package using the following command:

```bash
dotnet add package AutoGen.Gemini
```

### Step 2: Add using statement

[!code-csharp[](../../../samples/AutoGen.Gemini.Sample/Chat_With_Google_Gemini.cs?name=Using)]

### Step 3: Create a Gemini agent

[!code-csharp[](../../../samples/AutoGen.Gemini.Sample/Chat_With_Google_Gemini.cs?name=Create_Gemini_Agent)]

### Step 4: Chat with Gemini

[!code-csharp[](../../../samples/AutoGen.Gemini.Sample/Chat_With_Google_Gemini.cs?name=Chat_With_Google_Gemini)]