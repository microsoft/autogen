// Copyright (c) Microsoft Corporation. All rights reserved.
// InMemoryRuntimeIntegrationTests.cs
using Xunit.Abstractions;

namespace Microsoft.AutoGen.Integration.Tests;

public class InMemoryRuntimeIntegrationTests(ITestOutputHelper testOutput)
{

    [Theory, Trait("Category", "Integration")]
    [MemberData(nameof(AppHostAssemblies))]
    public async Task HelloAgentsE2EInMemory(string appHostAssemblyPath)
    {
        var appHost = await DistributedApplicationTestFactory.CreateAsync(appHostAssemblyPath, testOutput);
        await using var app = await appHost.BuildAsync().WaitAsync(TimeSpan.FromSeconds(15));

        await app.StartAsync().WaitAsync(TimeSpan.FromSeconds(120));
        await app.WaitForResourcesAsync().WaitAsync(TimeSpan.FromSeconds(120));

        await app.StartAsync().WaitAsync(TimeSpan.FromSeconds(120));
        await app.WaitForResourcesAsync().WaitAsync(TimeSpan.FromSeconds(120));

        //sleep 5 seconds to make sure the app is running
        await Task.Delay(15000);
        app.EnsureNoErrorsLogged();
        app.EnsureLogContains("Hello World");
        app.EnsureLogContains("HelloAgent said Goodbye");

        await app.StopAsync().WaitAsync(TimeSpan.FromSeconds(15));
    }
    public static TheoryData<string> AppHostAssemblies()
    {
        var appHostAssemblies = GetSamplesAppHostAssemblyPaths();
        var theoryData = new TheoryData<string, bool>();
        return new(appHostAssemblies.Select(p => Path.GetRelativePath(AppContext.BaseDirectory, p)));
    }
    private static IEnumerable<string> GetSamplesAppHostAssemblyPaths()
    {
        // All the AppHost projects are referenced by this project so we can find them by looking for all their assemblies in the base directory
        return Directory.GetFiles(AppContext.BaseDirectory, "HelloAgent.AppHost.dll")
            .Where(fileName => !fileName.EndsWith("Aspire.Hosting.AppHost.dll", StringComparison.OrdinalIgnoreCase));
    }
}
