// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.Extensions.Hosting;

var appHost = DistributedApplication.CreateBuilder();
appHost.AddProject<Projects.HelloAgent>("HelloAgentsDotNetInMemoryRuntime");
var app = appHost.Build();
await app.StartAsync();
await app.WaitForShutdownAsync();
