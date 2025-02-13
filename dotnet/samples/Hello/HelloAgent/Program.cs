// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Samples;

// Set up app builder for in-process runtime, allow message delivery to self, and add the Hello agent
AgentsAppBuilder appBuilder = new AgentsAppBuilder()
    .UseInProcessRuntime(deliverToSelf: true)
    .AddAgent<HelloAgent>("HelloAgent");
var app = await appBuilder.BuildAsync(); // Build the app
// Create a custom message type from proto and define message
NewMessageReceived message = new NewMessageReceived { Message = "Hello World!" };
await app.PublishMessageAsync(message, new TopicId("HelloTopic")); // Publish custom message (handler has been set in HelloAgent)
await app.WaitForShutdownAsync(); // Wait for shutdown from agent
