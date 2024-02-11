// Copyright (c) Microsoft Corporation. All rights reserved.
// Example08_LMStudio.cs

using AutoGen.LMStudio;

namespace AutoGen.BasicSample;

public class Example08_LMStudio
{
    public static async Task RunAsync()
    {
        // this example shows how to connect to LLM service from LM Studio in AutoGen
        var config = new LMStudioConfig("localhost", 1234);
        var lmAgent = new LMStudioAgent("asssistant", config: config)
            .RegisterPrintFormatMessageHook();

        await lmAgent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
    }
}
