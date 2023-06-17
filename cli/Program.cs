using System.CommandLine;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.TextEmbedding;
using Microsoft.SemanticKernel.Connectors.Memory.Qdrant;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Microsoft.SemanticKernel.Reliability;
using skills;

class Program
{
    static async Task Main(string[] args)
    {

        var maxRetryOption = new Option<int?>(
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
        doItCommand.SetHandler(async (file) => await ChainFunctions(file.FullName, maxRetry), fileOption, maxRetryOption);
        doCommand.AddCommand(doItCommand);

        var pmCommand = new Command("pm", "Commands for the PM team");
        var pmReadmeCommand = new Command("readme", "Produce a Readme for a given input");
        pmReadmeCommand.SetHandler(async (file) => await CallWithFile<string>(nameof(PM), PM.Readme , file.FullName), fileOption);

        var pmBootstrapCommand = new Command("bootstrap", "Bootstrap a project for a given input");
        pmBootstrapCommand.SetHandler(async (file) => await CallWithFile<string>(nameof(PM), PM.BootstrapProject, file.FullName), fileOption);

        pmCommand.AddCommand(pmReadmeCommand);
        pmCommand.AddCommand(pmBootstrapCommand);

        var devleadCommand = new Command("devlead", "Commands for the Dev Lead team");
        var devleadPlanCommand = new Command("plan", "Plan the work for a given input");
        devleadPlanCommand.SetHandler(async (file) => await CallWithFile<DevLeadPlanResponse>(nameof(DevLead), DevLead.Plan, file.FullName), fileOption);
        devleadCommand.AddCommand(devleadPlanCommand);

        var devCommand = new Command("dev", "Commands for the Dev team");
        var devPlanCommand = new Command("plan", "Implement the module for a given input");
        devPlanCommand.SetHandler(async (file) => await CallWithFile<string>(nameof(Developer), Developer.Implement, file.FullName), fileOption);
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

        var readme = await CallWithFile<string>(nameof(PM), PM.Readme , file);
        string readmeFile = Path.Combine(outputPath.FullName, "README.md");
        await SaveToFile(readmeFile, readme);

        var script = await CallWithFile<string>(nameof(PM), PM.BootstrapProject, file);
        await sandboxSkill.RunInDotnetAlpineAsync(script);
        await SaveToFile(Path.Combine(outputPath.FullName, "bootstrap.sh"), script);

        var plan = await CallWithFile<DevLeadPlanResponse>(nameof(DevLead), DevLead.Plan, readmeFile);
        await SaveToFile(Path.Combine(outputPath.FullName, "plan.json"), JsonSerializer.Serialize(plan));

        var implementationTasks = plan.steps.SelectMany(
            (step) => step.subtasks.Select(
                async (subtask) => {
                        var implementationResult = await CallFunction<string>(nameof(Developer), Developer.Implement, subtask.LLM_prompt);
                        var improvementResult = await CallFunction<string>(nameof(Developer), Developer.Improve, subtask.LLM_prompt); 
                        await sandboxSkill.RunInDotnetAlpineAsync(implementationResult);
                        await SaveToFile(Path.Combine(outputPath.FullName, $"{step.step}-{subtask.subtask}.sh"), improvementResult);
                        return improvementResult; }));
        await Task.WhenAll(implementationTasks);
    }

    public static async Task SaveToFile(string filePath, string content)
    {
        await File.WriteAllTextAsync(filePath, content);
    }

    public static async Task<T> CallWithFile<T>(string skillName, string functionName, string filePath)
    { 
        if(!File.Exists(filePath))
            throw new FileNotFoundException($"File not found: {filePath}", filePath);
        var input = File.ReadAllText(filePath);
        return await CallFunction<T>(skillName, functionName, input);
    }

    public static async Task<T> CallFunction<T>(string skillName, string functionName, string input)
    {
        var kernelSettings = KernelSettings.LoadSettings();
        var kernelConfig = new KernelConfig();

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
                .SetMinimumLevel(kernelSettings.LogLevel ?? LogLevel.Warning)
                .AddConsole()
                .AddDebug();
        });
        var memoryStore = new QdrantMemoryStore(new QdrantVectorDbClient("http://qdrant", 1536, port: 6333));
        var embedingGeneration = new AzureTextEmbeddingGeneration(kernelSettings.EmbeddingDeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey);
        var semanticTextMemory = new SemanticTextMemory(memoryStore, embedingGeneration);

        var kernel = new KernelBuilder()
                            .WithLogger(loggerFactory.CreateLogger<IKernel>())
                            .WithAzureChatCompletionService(kernelSettings.DeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey, true, kernelSettings.ServiceId, true)
                            .WithMemory(semanticTextMemory)
                            .WithConfiguration(kernelConfig)
                            .Configure(c => c.SetDefaultHttpRetryConfig(new HttpRetryConfig
                            {
                                MaxRetryCount = 6,
                                UseExponentialBackoff = true,
                                //  MinRetryDelay = TimeSpan.FromSeconds(2),
                                //  MaxRetryDelay = TimeSpan.FromSeconds(8),
                                MaxTotalRetryTime = TimeSpan.FromSeconds(30),
                                //  RetryableStatusCodes = new[] { HttpStatusCode.TooManyRequests, HttpStatusCode.RequestTimeout },
                                //  RetryableExceptions = new[] { typeof(HttpRequestException) }
                            }))
                            .Build();
        Console.WriteLine($"Calling skill '{skillName}' function '{functionName}' with input '{input}'");
        var interestingMemories = kernel.Memory.SearchAsync("waf-pages", input, 2);
        var wafContext = "Consider the following architectural guidelines:";
        await foreach (var memory in interestingMemories)
        {
            wafContext += $"\n {memory.Metadata.Text}";
        }
        var skillConfig = SemanticFunctionConfig.ForSkillAndFunction(skillName, functionName);
        var function = kernel.CreateSemanticFunction(skillConfig.PromptTemplate, skillConfig.Name, skillConfig.SkillName,
                                                   skillConfig.Description, skillConfig.MaxTokens, skillConfig.Temperature,
                                                   skillConfig.TopP, skillConfig.PPenalty, skillConfig.FPenalty);

        var context = new ContextVariables();
        context.Set("input", input);
        context.Set("wafContext", wafContext);

        var answer = await kernel.RunAsync(context, function).ConfigureAwait(false);
        var result = typeof(T) != typeof(string) ? JsonSerializer.Deserialize<T>(answer.ToString()) : (T)(object)answer.ToString();
        Console.WriteLine(answer);
        return result;
    }
}

public static class PM { public static string Readme = "Readme"; public static string BootstrapProject = "BootstrapProject"; }
public static class DevLead { public static string Plan="Plan"; }
public static class Developer { public static string Implement="Implement"; public static string Improve="Improve";}
