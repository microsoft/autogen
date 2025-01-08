// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Runtime.Grpc;

var builder = WebApplication.CreateBuilder(args);

builder.AddGrpcRuntime(inMemoryOrleans: true);

var app = builder.Build();

app.MapAgentService();

app.Run();
