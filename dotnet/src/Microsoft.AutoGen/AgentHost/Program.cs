// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs
using Microsoft.Extensions.Hosting;

var app = await Microsoft.AutoGen.Runtime.Grpc.Host.StartAsync(local: false, useGrpc: true).ConfigureAwait(false);
await app.WaitForShutdownAsync();
