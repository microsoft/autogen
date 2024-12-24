// Copyright (c) Microsoft Corporation. All rights reserved.
// HelloAppHostIntegrationTests.cs

using System.Text.Json;
using Xunit.Abstractions;

namespace Microsoft.AutoGen.Integration.Tests;

public class HelloAppHostIntegrationTests(ITestOutputHelper testOutput)
{
    [Theory, Trait("type", "integration")]
    [MemberData(nameof(AppHostAssemblies))]
    public async Task AppHostRunsCleanly(string appHostPath)
    {
        var appHost = await DistributedApplicationTestFactory.CreateAsync(appHostPath, testOutput);
        await using var app = await appHost.BuildAsync().WaitAsync(TimeSpan.FromSeconds(15));

        await app.StartAsync().WaitAsync(TimeSpan.FromSeconds(120));
        await app.WaitForResourcesAsync().WaitAsync(TimeSpan.FromSeconds(120));

        app.EnsureNoErrorsLogged();
        await app.StopAsync().WaitAsync(TimeSpan.FromSeconds(15));
    }

    [Theory, Trait("type", "integration")]
    [MemberData(nameof(TestEndpoints))]
    public async Task AppHostLogsHelloAgentE2E(TestEndpoints testEndpoints)
    {
        var appHostName = testEndpoints.AppHost!;
        var appHostPath = $"{appHostName}.dll";
        var appHost = await DistributedApplicationTestFactory.CreateAsync(appHostPath, testOutput);
        await using var app = await appHost.BuildAsync().WaitAsync(TimeSpan.FromSeconds(15));

        await app.StartAsync().WaitAsync(TimeSpan.FromSeconds(120));
        await app.WaitForResourcesAsync().WaitAsync(TimeSpan.FromSeconds(120));
        if (testEndpoints.WaitForResources?.Count > 0)
        {
            // Wait until each resource transitions to the required state
            var timeout = TimeSpan.FromMinutes(5);
            foreach (var (ResourceName, TargetState) in testEndpoints.WaitForResources)
            {
                await app.WaitForResource(ResourceName, TargetState).WaitAsync(timeout);
            }
        }
        //sleep to make sure the app is running
        await Task.Delay(20000);
        app.EnsureNoErrorsLogged();
        app.EnsureLogContains("HelloAgent said Goodbye");
        app.EnsureLogContains("Wild Hello from Python!");

        await app.StopAsync().WaitAsync(TimeSpan.FromSeconds(15));
    }
    public static TheoryData<string> AppHostAssemblies()
    {
        var appHostAssemblies = GetSamplesAppHostAssemblyPaths();
        var theoryData = new TheoryData<string, bool>();
        return new(appHostAssemblies.Select(p => Path.GetRelativePath(AppContext.BaseDirectory, p)));
    }

    public static TheoryData<TestEndpoints> TestEndpoints() =>
        new([
            new TestEndpoints("Hello.AppHost", new() {
                { "backend", ["/"] }
            }),
        ]);

    private static IEnumerable<string> GetSamplesAppHostAssemblyPaths()
    {
        // All the AppHost projects are referenced by this project so we can find them by looking for all their assemblies in the base directory
        return Directory.GetFiles(AppContext.BaseDirectory, "*.AppHost.dll")
            .Where(fileName => !fileName.EndsWith("Aspire.Hosting.AppHost.dll", StringComparison.OrdinalIgnoreCase));
    }
}

public class TestEndpoints : IXunitSerializable
{
    // Required for deserialization
    public TestEndpoints() { }

    public TestEndpoints(string appHost, Dictionary<string, List<string>> resourceEndpoints)
    {
        AppHost = appHost;
        ResourceEndpoints = resourceEndpoints;
    }

    public string? AppHost { get; set; }

    public List<ResourceWait>? WaitForResources { get; set; }

    public Dictionary<string, List<string>>? ResourceEndpoints { get; set; }

    public void Deserialize(IXunitSerializationInfo info)
    {
        AppHost = info.GetValue<string>(nameof(AppHost));
        WaitForResources = JsonSerializer.Deserialize<List<ResourceWait>>(info.GetValue<string>(nameof(WaitForResources)));
        ResourceEndpoints = JsonSerializer.Deserialize<Dictionary<string, List<string>>>(info.GetValue<string>(nameof(ResourceEndpoints)));
    }

    public void Serialize(IXunitSerializationInfo info)
    {
        info.AddValue(nameof(AppHost), AppHost);
        info.AddValue(nameof(WaitForResources), JsonSerializer.Serialize(WaitForResources));
        info.AddValue(nameof(ResourceEndpoints), JsonSerializer.Serialize(ResourceEndpoints));
    }

    public override string? ToString() => $"{AppHost} ({ResourceEndpoints?.Count ?? 0} resources)";

    public class ResourceWait(string resourceName, string targetState)
    {
        public string ResourceName { get; } = resourceName;

        public string TargetState { get; } = targetState;

        public void Deconstruct(out string resourceName, out string targetState)
        {
            resourceName = ResourceName;
            targetState = TargetState;
        }
    }
}
