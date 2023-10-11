using DotNet.Testcontainers.Builders;
using Microsoft.SemanticKernel.SkillDefinition;

public class SandboxSkill
{
    public async Task<string> RunInAlpineAsync(string input)
    {
        return await RunInContainer(input, "alpine");
    }

    public async Task<string> RunInDotnetAlpineAsync(string input)
    {
        return await RunInContainer(input, "mcr.microsoft.com/dotnet/sdk:7.0");
    }

    private async Task<string> RunInContainer(string input, string image)
    {
        var tempScriptFile = $"{Guid.NewGuid().ToString()}.sh";
        var tempScriptPath = $"./output/{tempScriptFile}";
        await File.WriteAllTextAsync(tempScriptPath, input);
        Directory.CreateDirectory(Path.Combine(Directory.GetCurrentDirectory(),"output", "src"));
        var dotnetContainer = new ContainerBuilder()
                            .WithName(Guid.NewGuid().ToString("D"))
                            .WithImage(image)
                            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(),"output", "src"), "/src")
                            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), tempScriptPath), $"/src/{tempScriptFile}")
                            .WithWorkingDirectory("/src")
                            .WithCommand("sh", tempScriptFile)
                            .Build();

        await dotnetContainer.StartAsync()
                            .ConfigureAwait(false);
        // Cleanup
        File.Delete(tempScriptPath);
        File.Delete(Path.Combine(Directory.GetCurrentDirectory(), "output", "src", tempScriptFile));
        return "";
    }
}