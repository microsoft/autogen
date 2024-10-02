// Copyright (c) Microsoft Corporation. All rights reserved.
// Example08_LMStudio.cs

#region lmstudio_using_statements
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using OpenAI;
#endregion lmstudio_using_statements

namespace AutoGen.BasicSample;

public class Example08_LMStudio
{
    public static async Task RunAsync()
    {
        #region lmstudio_example_1
        var endpoint = "http://localhost:1234";
        var openaiClient = new OpenAIClient("api-key", new OpenAIClientOptions
        {
            Endpoint = new Uri(endpoint),
        });

        var lmAgent = new OpenAIChatAgent(
            chatClient: openaiClient.GetChatClient("<does-not-matter>"),
            name: "assistant")
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        await lmAgent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");

        // output from assistant (the output below is generated using llama-2-chat-7b, the output may vary depending on the model used)
        //
        // Of course! To calculate the 100th number in the Fibonacci sequence using C#, you can use the following code:```
        // using System;
        // class FibonacciSequence {
        //     static int Fibonacci(int n) {
        //         if (n <= 1) {
        //             return 1;
        //         } else {
        //             return Fibonacci(n - 1) + Fibonacci(n - 2);
        //         }
        //     }
        //     static void Main() {
        //         Console.WriteLine("The 100th number in the Fibonacci sequence is: " + Fibonacci(100));
        //     }
        // }
        // ```
        // In this code, we define a function `Fibonacci` that takes an integer `n` as input and returns the `n`-th number in the Fibonacci sequence. The function uses a recursive approach to calculate the value of the sequence.
        // The `Main` method simply calls the `Fibonacci` function with the argument `100`, and prints the result to the console.
        // Note that this code will only work for positive integers `n`. If you want to calculate the Fibonacci sequence for other types of numbers, such as real or complex numbers, you will need to modify the code accordingly.
        #endregion lmstudio_example_1
    }
}
