using AutoGen.Core;
using AutoGen.Ollama;

namespace AutoGen.BasicSample;

public class Example15_Ollama
{
    public static async Task RunAsync()
    {
        var config = new OllamaConfig("localhost", 11434);

        // create assistant agent
        // You can specify any model Ollama supports.
        // See list here: https://ollama.com/library
        // Just make sure you "pull" the model using "ollama pull" first.
        var assistantAgent = new OllamaAgent("asssistant", config: config, "llama3")
            .RegisterPrintMessage();

        // set human input mode to ALWAYS so that user always provide input
        var userProxyAgent = new UserProxyAgent(
            name: "user",
            humanInputMode: HumanInputMode.ALWAYS)
            .RegisterPrintMessage();

        // start the conversation
        await userProxyAgent.InitiateChatAsync(
            receiver: assistantAgent,
            message: "Why is the sky blue?",
            maxRound: 10);

        Console.WriteLine("Thanks for using Ollama. https://ollama.com/blog/");
    }
}
