using AutoGen.GenericAPI;

namespace AutoGen.BasicSample;

public class Example10_GenericAPI
{
    public static async Task RunAsync()
    {
        string mistralApiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ??
                               throw new Exception("Please set MISTRAL_API_KEY environment variable.");
        var config = new GenericAgentConfig(mistralApiKey, "api.mistral.ai", "mistral-large-latest");
        MiddlewareAgent lmAgent = new GenericAgent("assistant", config)
            .RegisterPrintFormatMessageHook();

        await lmAgent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");

        // output from assistant (the output below is generated using mistral-large-latest, the output may vary depending on the model used)
        //
        //content: Sure, I'd be happy to help with that. Here's a simple C# code snippet that uses an iterative approach to calculate the 100th //Fibonacci number:
        //
        //```csharp
        //using System;
        //
        //class Program
        //{
        //    static void Main()
        //    {
        //        long prevPrev = 0;
        //        long prev = 1;
        //        long current = 0;
        //
        //        for (int i = 0; i < 100; i++)
        //        {
        //            if (i <= 1)
        //                current = i;
        //            else
        //            {
        //                current = prev + prevPrev;
        //                prevPrev = prev;
        //                prev = current;
        //            }
        //        }
        //
        //        Console.WriteLine("The 100th Fibonacci number is: " + current);
        //    }
        //}
        //```
        //
        //This code starts with the first two Fibonacci numbers, 0 and 1. It then enters a loop that runs 100 times. In each iteration of the loop,
        //it calculates the next Fibonacci number by adding the two previous ones. The `prevPrev` and `prev` variables are updated to hold the last
        //two Fibonacci numbers calculated. After the loop finishes, it prints the 100th Fibonacci number.
    }
}
