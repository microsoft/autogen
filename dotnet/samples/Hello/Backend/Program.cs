// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

// TODO: replace with container
//var app = await Microsoft.AutoGen.Agents.Host.StartAsync(local: false, useGrpc: true);
//await app.WaitForShutdownAsync();
var builder = WebApplication.CreateBuilder();
var app = builder.Build();
await app.WaitForShutdownAsync();
