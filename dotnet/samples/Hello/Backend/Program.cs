// Copyright (c) Microsoft. All rights reserved.
using Microsoft.Extensions.Hosting;

var app = await Microsoft.AutoGen.Runtime.Host.StartAsync(local: true);
await app.WaitForShutdownAsync();
