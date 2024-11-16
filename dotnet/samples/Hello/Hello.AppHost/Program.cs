// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

var builder = DistributedApplication.CreateBuilder(args);
var backend = builder.AddProject<Projects.Backend>("backend");
builder.AddProject<Projects.HelloAgent>("client").WithReference(backend).WaitFor(backend);
builder.Build().Run();
