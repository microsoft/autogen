The following example shows how to enable JSON mode in @AutoGen.OpenAI.OpenAIChatAgent.

[![](https://img.shields.io/badge/Open%20on%20Github-grey?logo=github)](https://github.com/microsoft/autogen/blob/main/dotnet/sample/AutoGen.OpenAI.Sample/Use_Json_Mode.cs)

## What is JSON mode?
JSON mode is a new feature in OpenAI which allows you to instruct model to always respond with a valid JSON object. This is useful when you want to constrain the model output to JSON format only.

> [!NOTE]
> Currently, JOSN mode is only supported by `gpt-4-turbo-preview` and `gpt-3.5-turbo-0125`. For more information (and limitations) about JSON mode, please visit [OpenAI API documentation](https://platform.openai.com/docs/guides/text-generation/json-mode).

## How to enable JSON mode in OpenAIChatAgent.

To enable JSON mode for @AutoGen.OpenAI.OpenAIChatAgent, set `responseFormat` to `ChatCompletionsResponseFormat.JsonObject` when creating the agent. Note that when enabling JSON mode, you also need to instruct the agent to output JSON format in its system message.

[!code-csharp[](../../sample/AutoGen.OpenAI.Sample/Use_Json_Mode.cs?name=create_agent)]

After enabling JSON mode, the `openAIClientAgent` will always respond in JSON format when it receives a message.

[!code-csharp[](../../sample/AutoGen.OpenAI.Sample/Use_Json_Mode.cs?name=chat_with_agent)]

When running the example, the output from `openAIClientAgent` will be a valid JSON object which can be parsed as `Person` class defined below. Note that in the output, the `address` field is missing because the address information is not provided in user input.

[!code-csharp[](../../sample/AutoGen.OpenAI.Sample/Use_Json_Mode.cs?name=person_class)]

The output will be:
```bash
Name: John
Age: 25
Done
```