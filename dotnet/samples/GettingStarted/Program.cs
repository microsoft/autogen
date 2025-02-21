// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs
#region snippet_Program
#region snippet_Program_funcs
using GettingStartedSample;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection.Extensions;
using ModifyF = System.Func<int, int>;
using TerminationF = System.Func<int, bool>;

ModifyF modifyFunc = (int x) => x - 1;
TerminationF runUntilFunc = (int x) =>
{
    return x <= 1;
};
#endregion snippet_Program_funcs

#region snippet_Program_builder
AgentsAppBuilder appBuilder = new AgentsAppBuilder();
appBuilder.UseInProcessRuntime();

appBuilder.Services.TryAddSingleton(modifyFunc);
appBuilder.Services.TryAddSingleton(runUntilFunc);

appBuilder.AddAgent<Checker>("Checker");
appBuilder.AddAgent<Modifier>("Modifier");

var app = await appBuilder.BuildAsync();
await app.StartAsync();
#endregion snippet_Program_builder

#region snippet_Program_publish
// Send the initial count to the agents app, running on the `local` runtime, and pass through the registered services via the application `builder`
await app.PublishMessageAsync(new CountMessage
{
    Content = 10
}, new TopicId("default"));

// Run until application shutdown
await app.WaitForShutdownAsync();
#endregion snippet_Program_publish
#endregion snippet_Program
