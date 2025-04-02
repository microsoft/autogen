// Copyright (c) Microsoft Corporation. All rights reserved.
// TestBase.cs

namespace Microsoft.AutoGen.Core.Grpc.Tests;

public class TestBase
{
    public TestBase()
    {
        try
        {
            // For some reason the first call to StartAsync() throws when these tests
            // run in parallel, even though the port does not actually collide between
            // different instances of GrpcAgentRuntimeFixture. This is a workaround.
            _ = new GrpcAgentRuntimeFixture().StartAsync().Result;
        }
        catch (Exception e)
        {
            Console.WriteLine(e);
        }
    }
}
