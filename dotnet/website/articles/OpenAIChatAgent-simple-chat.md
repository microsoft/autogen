The following example shows how to create an @AutoGen.OpenAI.OpenAIChatAgent and chat with it.

Firsly, import the required namespaces:
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/OpenAICodeSnippet.cs?name=using_statement)]

Then, create an @AutoGen.OpenAI.OpenAIChatAgent and chat with it:
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/OpenAICodeSnippet.cs?name=create_openai_chat_agent)]

@AutoGen.OpenAI.OpenAIChatAgent also supports streaming chat via @AutoGen.Core.IAgent.GenerateStreamingReplyAsync*.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/OpenAICodeSnippet.cs?name=create_openai_chat_agent_streaming)]