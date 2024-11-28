// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs
using Microsoft.AutoGen.DistributedRuntime;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.AddAgentService();

var app = builder.Build();

app.MapDefaultEndpoints();
app.MapAgentService();

app.Run();
