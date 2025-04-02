// Copyright (c) Microsoft Corporation. All rights reserved.
// InMemoryRuntimeIntegrationTests.cs
using Xunit.Abstractions;

namespace Microsoft.AutoGen.Integration.Tests;

public class InMemoryRuntimeIntegrationTests(ITestOutputHelper testOutput)
{
    [Fact]
    public async Task HelloAgentsE2EInMemory()
    {
        // Locate InMemoryTests.AppHost.dll in the test output folder
        var appHostAssemblyPath = Directory.GetFiles(AppContext.BaseDirectory, "InMemoryTests.AppHost.dll", SearchOption.AllDirectories)
            .FirstOrDefault()
            ?? throw new FileNotFoundException("Could not find InMemoryTests.AppHost.dll in the test output folder");
        var appHost = await DistributedApplicationTestFactory.CreateAsync(appHostAssemblyPath, testOutput);
        await using var app = await appHost.BuildAsync().WaitAsync(TimeSpan.FromSeconds(15));

        // Start the application and wait for resources
        await app.StartAsync().WaitAsync(TimeSpan.FromSeconds(120));
        await app.WaitForResourcesAsync().WaitAsync(TimeSpan.FromSeconds(120));

        // Sleep 5 seconds to ensure the app is up
        await Task.Delay(5000);
        app.EnsureNoErrorsLogged();
        app.EnsureLogContains("Hello World");
        app.EnsureLogContains("HelloAgent said Goodbye");

        await app.StopAsync().WaitAsync(TimeSpan.FromSeconds(15));
    }
}
