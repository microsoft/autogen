// Copyright (c) Microsoft. All rights reserved.

var builder = DistributedApplication.CreateBuilder(args);
var backend = builder.AddProject<Projects.Backend>("backend");
builder.AddProject<Projects.HelloAgent>("client").WithReference(backend).WaitFor(backend);
builder.Build().Run();
