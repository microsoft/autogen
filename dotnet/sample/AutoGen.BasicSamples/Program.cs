// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

//await Example07_Dynamic_GroupChat_Calculate_Fibonacci.RunAsync();

using AutoGen.BasicSample;

//Define allSamples collection for all examples
List<Tuple<string, Func<Task>>> allSamples = new List<Tuple<string, Func<Task>>>();

// When a new sample is created please add them to the allSamples collection
allSamples.Add(new Tuple<string, Func<Task>>("Assistant Agent", async () => { await Example01_AssistantAgent.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("Two-agent Math Chat", async () => { await Example02_TwoAgent_MathChat.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("Agent Function Call", async () => { await Example03_Agent_FunctionCall.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("Dynamic Group Chat Coding Task", async () => { await Example04_Dynamic_GroupChat_Coding_Task.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("DALL-E and GPT4v", async () => { await Example05_Dalle_And_GPT4V.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("User Proxy Agent", async () => { await Example06_UserProxyAgent.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("Dynamic Group Chat - Calculate Fibonacci", async () => { await Example07_Dynamic_GroupChat_Calculate_Fibonacci.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("LM Studio", async () => { await Example08_LMStudio.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("Semantic Kernel", async () => { await Example10_SemanticKernel.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("Sequential Group Chat", async () => { await Sequential_GroupChat_Example.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("Two Agent - Fill Application", async () => { await TwoAgent_Fill_Application.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("Mistal Client Agent - Token Count", async () => { await Example14_MistralClientAgent_TokenCount.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("GPT4v - Binary Data Image", async () => { await Example15_GPT4V_BinaryDataImageMessage.RunAsync(); }));
allSamples.Add(new Tuple<string, Func<Task>>("ReAct Agent", async () => { await Example17_ReActAgent.RunAsync(); }));


int idx = 1;
Dictionary<int, Tuple<string, Func<Task>>> map = new Dictionary<int, Tuple<string, Func<Task>>>();
Console.WriteLine("Available Examples:\n\n");
foreach (Tuple<string, Func<Task>> sample in allSamples)
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
    int val = Convert.ToInt32(input);
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



