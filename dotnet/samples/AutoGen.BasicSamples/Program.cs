// Copyright (c) Microsoft. All rights reserved.

//await Example07_Dynamic_GroupChat_Calculate_Fibonacci.RunAsync();

using AutoGen.BasicSample;

//Define allSamples collection for all examples
var allSamples = new List<(string, Func<Task>)>
{
    // When a new sample is created please add them to the allSamples collection
    ("Assistant Agent", Example01_AssistantAgent.RunAsync),
    ("Two-agent Math Chat", Example02_TwoAgent_MathChat.RunAsync),
    ("Agent Function Call", Example03_Agent_FunctionCall.RunAsync),
    ("Dynamic Group Chat Coding Task", Example04_Dynamic_GroupChat_Coding_Task.RunAsync),
    ("DALL-E and GPT4v", Example05_Dalle_And_GPT4V.RunAsync),
    ("User Proxy Agent", Example06_UserProxyAgent.RunAsync),
    ("Dynamic Group Chat - Calculate Fibonacci", Example07_Dynamic_GroupChat_Calculate_Fibonacci.RunAsync),
    ("LM Studio", Example08_LMStudio.RunAsync),
    ("Semantic Kernel", Example10_SemanticKernel.RunAsync),
    ("Sequential Group Chat", Sequential_GroupChat_Example.RunAsync),
    ("Two Agent - Fill Application", TwoAgent_Fill_Application.RunAsync),
    ("Mistral Client Agent - Token Count", Example14_MistralClientAgent_TokenCount.RunAsync),
    ("GPT4v - Binary Data Image", Example15_GPT4V_BinaryDataImageMessage.RunAsync),
    ("ReAct Agent", Example17_ReActAgent.RunAsync)
};

Console.WriteLine("Available Examples:\n\n");
var idx = 1;
var map = new Dictionary<int, (string, Func<Task>)>();
foreach (var sample in allSamples)
{
    map.Add(idx, sample);
    Console.WriteLine("{0}. {1}", idx++, sample.Item1);
}

Console.WriteLine("\n\nEnter your selection:");

while (true)
{
    var input = Console.ReadLine();
    if (input == "exit")
    {
        break;
    }
    var val = Convert.ToInt32(input);
    if (!map.ContainsKey(val))
    {
        Console.WriteLine("Invalid choice");
    }
    else
    {
        Console.WriteLine("\nRunning {0}", map[val].Item1);
        await map[val].Item2.Invoke();
    }
}
