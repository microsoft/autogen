// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.AutoGen.DistributedRuntime;
using Microsoft.AspNetCore.Builder;

var builder = WebApplication.CreateBuilder(args);

builder.AddAgentService(inMemoryOrleans: true, useGrpc: true);

var app = builder.Build();

app.MapAgentService();

app.Run();
