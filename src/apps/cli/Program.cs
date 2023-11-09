using System.CommandLine;
using System.Text.Json;
using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.TextEmbedding;
using Microsoft.SemanticKernel.Connectors.Memory.Qdrant;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;


class Program
{
    static async Task Main(string[] args)
    {

        var maxRetryOption = new Option<int>(
            name: "--maxRetry",
            description: "The number of retires to use if throttled",
            getDefaultValue: () => 6);

        var fileOption = new Option<FileInfo?>(
            name: "--file",
            description: "The file used for input to the skill function");

        var rootCommand = new RootCommand("CLI tool for the AI Dev team");
        rootCommand.AddGlobalOption(fileOption);
        rootCommand.Add(maxRetryOption);

        var doCommand = new Command("do", "Doers :) ");
        var doItCommand = new Command("it", "Do it!");
        doItCommand.SetHandler(async (file, maxRetry) => await ChainFunctions(file.FullName, maxRetry), fileOption, maxRetryOption);
        doCommand.AddCommand(doItCommand);

        var pmCommand = new Command("pm", "Commands for the PM team");
        var pmReadmeCommand = new Command("readme", "Produce a Readme for a given input");
        pmReadmeCommand.SetHandler(async (file, maxRetry) => await CallWithFile<string>(nameof(PM), PM.Readme, file.FullName, maxRetry), fileOption, maxRetryOption);

        var pmBootstrapCommand = new Command("bootstrap", "Bootstrap a project for a given input");
        pmBootstrapCommand.SetHandler(async (file, maxRetry) => await CallWithFile<string>(nameof(PM), PM.BootstrapProject, file.FullName, maxRetry), fileOption, maxRetryOption);

        pmCommand.AddCommand(pmReadmeCommand);
        pmCommand.AddCommand(pmBootstrapCommand);

        var devleadCommand = new Command("devlead", "Commands for the Dev Lead team");
        var devleadPlanCommand = new Command("plan", "Plan the work for a given input");
        devleadPlanCommand.SetHandler(async (file, maxRetry) => await CallWithFile<DevLeadPlanResponse>(nameof(DevLead), DevLead.Plan, file.FullName, maxRetry), fileOption, maxRetryOption);
        devleadCommand.AddCommand(devleadPlanCommand);

        var devCommand = new Command("dev", "Commands for the Dev team");
        var devPlanCommand = new Command("plan", "Implement the module for a given input");
        devPlanCommand.SetHandler(async (file, maxRetry) => await CallWithFile<string>(nameof(Developer), Developer.Implement, file.FullName, maxRetry), fileOption, maxRetryOption);
        devCommand.AddCommand(devPlanCommand);

        rootCommand.AddCommand(pmCommand);
        rootCommand.AddCommand(devleadCommand);
        rootCommand.AddCommand(devCommand);
        rootCommand.AddCommand(doCommand);

        await rootCommand.InvokeAsync(args);
    }

    public static async Task ChainFunctions(string file, int maxRetry)
    {
        var sandboxSkill = new SandboxSkill();
        var outputPath = Directory.CreateDirectory("output");

        Console.WriteLine($"Using output directory: {outputPath}");

        var readme = await CallWithFile<string>(nameof(PM), PM.Readme, file, maxRetry);
        string readmeFile = Path.Combine(outputPath.FullName, "README.md");
        await SaveToFile(readmeFile, readme);
        Console.WriteLine($"Saved README to {readmeFile}");

        var script = await CallWithFile<string>(nameof(PM), PM.BootstrapProject, file, maxRetry);
        await sandboxSkill.RunInDotnetAlpineAsync(script);
        await SaveToFile(Path.Combine(outputPath.FullName, "bootstrap.sh"), script);
        Console.WriteLine($"Saved bootstrap script to {outputPath.FullName}bootstrap.sh");

        var plan = await CallWithFile<DevLeadPlanResponse>(nameof(DevLead), DevLead.Plan, readmeFile, maxRetry);
        await SaveToFile(Path.Combine(outputPath.FullName, "plan.json"), JsonSerializer.Serialize(plan));
        Console.WriteLine($"Using Plan: \n {plan}");

        var implementationTasks = plan.steps.SelectMany(
            (step) => step.subtasks.Select(
                async (subtask) =>
                {
                    Console.WriteLine($"Implementing {step.step}-{subtask.subtask}");
                    var implementationResult = string.Empty;
                    while (true)
                    {
                        try
                        {
                            implementationResult = await CallFunction<string>(nameof(Developer), Developer.Implement, subtask.prompt, maxRetry);
                            break;
                        }
                        catch (Exception ex)
                        {
                            if (ex.Message.Contains("TooMany"))
                            {
                                Console.WriteLine("Throttled, retrying...");
                                continue;
                            }
                            throw;
                        }
                    }
                    await sandboxSkill.RunInDotnetAlpineAsync(implementationResult);
                    await SaveToFile(Path.Combine(outputPath.FullName, $"{step.step}-{subtask.subtask}.sh"), implementationResult);
                    return implementationResult;
                }));
        await Task.WhenAll(implementationTasks);
    }

    public static async Task SaveToFile(string filePath, string content)
    {
        await File.WriteAllTextAsync(filePath, content);
    }

    public static async Task<T> CallWithFile<T>(string skillName, string functionName, string filePath, int maxRetry)
    {
        if (!File.Exists(filePath))
            throw new FileNotFoundException($"File not found: {filePath}", filePath);
        var input = File.ReadAllText(filePath);
        return await CallFunction<T>(skillName, functionName, input, maxRetry);
    }

    public static async Task<T> CallFunction<T>(string skillName, string functionName, string input, int maxRetry)
    {
        var kernelSettings = KernelSettings.LoadSettings();

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
                .SetMinimumLevel(kernelSettings.LogLevel ?? LogLevel.Warning)
                .AddConsole()
                .AddDebug();
        });
        var memoryStore = new QdrantMemoryStore(new QdrantVectorDbClient("http://qdrant:6333", 1536));
        var embedingGeneration = new AzureTextEmbeddingGeneration(kernelSettings.EmbeddingDeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey);
        var semanticTextMemory = new SemanticTextMemory(memoryStore, embedingGeneration);

        var kernel = new KernelBuilder()
                            .WithLoggerFactory(loggerFactory)
                            .WithAzureChatCompletionService(kernelSettings.DeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey, true, kernelSettings.ServiceId, true)
                            .WithMemory(semanticTextMemory)
                            .Build();


                            
        //Console.WriteLine($"Calling skill '{skillName}' function '{functionName}' with input '{input}'");
        var interestingMemories = kernel.Memory.SearchAsync("waf-pages", input, 2);
        var wafContext = "Consider the following architectural guidelines:";
        await foreach (var memory in interestingMemories)
        {
            wafContext += $"\n {memory.Metadata.Text}";
        }
        var promptTemplate = Skills.ForSkillAndFunction(skillName, functionName);
        var function = kernel.CreateSemanticFunction(promptTemplate);

        var context = new ContextVariables();
        context.Set("input", input);
        context.Set("wafContext", wafContext);

        var answer = await kernel.RunAsync(context, function).ConfigureAwait(false);
        var result = typeof(T) != typeof(string) ? JsonSerializer.Deserialize<T>(answer.ToString()) : (T)(object)answer.ToString();
        //Console.WriteLine(answer);

        return result;
    }
}

public static class PM { public static string Readme = "Readme"; public static string BootstrapProject = "BootstrapProject"; }
public static class DevLead { public static string Plan = "Plan"; }
public static class Developer { public static string Implement = "Implement"; public static string Improve = "Improve"; }
