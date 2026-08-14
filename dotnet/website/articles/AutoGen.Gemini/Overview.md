# AutoGen.Gemini Overview

AutoGen.Gemini is a package that provides seamless integration with Google Gemini. It provides the following agent:

- @AutoGen.Gemini.GeminiChatAgent: The agent that connects to Google Gemini or Vertex AI Gemini. It supports chat, multi-modal chat, and function call.

AutoGen.Gemini also provides the following middleware:
- @AutoGen.Gemini.GeminiMessageConnector: The middleware that converts the Gemini message to AutoGen built-in message type.

## Examples

You can find more examples under the [gemini sample project](https://github.com/microsoft/autogen/tree/main/dotnet/samples/AutoGen.Gemini.Sample)