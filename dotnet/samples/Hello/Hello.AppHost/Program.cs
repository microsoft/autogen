// Copyright (c) Microsoft. All rights reserved.

var builder = DistributedApplication.CreateBuilder(args);
builder.AddProject<Projects.Backend>("backend");
builder.AddProject<Projects.HelloAgent>("client");
builder.Build().Run();
