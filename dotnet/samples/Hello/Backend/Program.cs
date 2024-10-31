// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.Extensions.Hosting;

var app = await Microsoft.AutoGen.Agents.Host.StartAsync(local: true);
await app.WaitForShutdownAsync();
