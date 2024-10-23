// Copyright (c) Microsoft. All rights reserved.

using Microsoft.AutoGen.Runtime;
var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.AddAgentService();

var app = builder.Build();

app.MapDefaultEndpoints();
app.MapAgentService();

app.Run();
