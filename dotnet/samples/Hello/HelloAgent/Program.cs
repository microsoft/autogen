// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.AutoGen.Core.Grpc;
using Samples;

string? hostAddress = null;
bool in_host_address = false;
bool sendHello = true;
foreach (string arg in args)
{
    switch (arg)
    {
        case "--host":
            in_host_address = true;
            break;
        case "--nosend":
            sendHello = false;
            break;
        case "-h":
        case "--help":
            PrintHelp();
            Environment.Exit(0);
            break;
        default:
            if (in_host_address)
            {
                hostAddress = arg;
            }
            break;
    }
}

hostAddress ??= Environment.GetEnvironmentVariable("AGENT_HOST");
var appBuilder = new AgentsAppBuilder(); // Create app builder
// if we are using distributed, we need the AGENT_HOST var defined and then we will use the grpc runtime

bool usingGrpc = false;
if (hostAddress is string agentHost)
{
    usingGrpc = true;
    Console.WriteLine($"connecting to {agentHost}");
    appBuilder.AddGrpcAgentWorker(agentHost)
        .AddAgent<HelloAgent>("HelloAgent");
}
else
{
    // Set up app builder for in-process runtime, allow message delivery to self, and add the Hello agent
    appBuilder.UseInProcessRuntime(deliverToSelf: true).AddAgent<HelloAgent>("HelloAgent");
}
var app = await appBuilder.BuildAsync(); // Build the app
await app.StartAsync();
// Create a custom message type from proto and define message

if (sendHello)
{
    var message = new NewMessageReceived { Message = "Hello World!" };
    await app.PublishMessageAsync(message, new TopicId("HelloTopic")).ConfigureAwait(false); // Publish custom message (handler has been set in HelloAgent)
}
else if (!usingGrpc)
{
    Console.Write("Warning: Using --nosend with the InProcessRuntime will hang. Terminating.");
    Environment.Exit(-1);
}

await app.WaitForShutdownAsync().ConfigureAwait(false); // Wait for shutdown from agent

static void PrintHelp()
{
    /*
     HelloAgent [--host <hostAddress>] [--nosend]
       --host Use gRPC gateway at <hostAddress>; this can also be set using the AGENT_HOST Environment Variable
       --nosend Do not send the starting message. Note: This means HelloAgent will wait until some other agent will send
                that message. This will not work when using the InProcessRuntime.
     */
    Console.WriteLine("HelloAgent [--host <hostAddress>] [--nosend]");
    Console.WriteLine("  --host \tUse gRPC gateway at <hostAddress>; this can also be set using the AGENT_HOST Environment Variable");
    Console.WriteLine("  --nosend \tDo not send the starting message. Note: This means HelloAgent will wait until some other agent will send");
}
