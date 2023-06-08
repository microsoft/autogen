using System.CommandLine;
using System.Text.Json;

class Program
{
    static async Task Main(string[] args)
    {
        var fileOption = new Option<FileInfo?>(
            name: "--file",
            description: "The file used for input to the skill function");

        var rootCommand = new RootCommand("CLI tool for the AI Dev team");
        rootCommand.AddGlobalOption(fileOption);

        var doCommand = new Command("do", "Doers :) ");
        var doItCommand = new Command("it", "Do it!");
        doItCommand.SetHandler(async (file) => await ChainFunctions(file.FullName), fileOption);
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

    public static async Task ChainFunctions(string file)
    {
        var sandboxSkill = new SandboxSkill();
        var outputPath = Directory.CreateDirectory("output");

        var readme = await CallWithFile<string>(nameof(PM), PM.Readme , file);
        await SaveToFile(Path.Combine(outputPath.FullName, "README.md"), readme);

        var script = await CallWithFile<string>(nameof(PM), PM.BootstrapProject, file);
        await sandboxSkill.RunInDotnetAlpineAsync(script);
        await SaveToFile(Path.Combine(outputPath.FullName, "bootstrap.sh"), script);

        var plan = await CallWithFile<DevLeadPlanResponse>(nameof(DevLead), DevLead.Plan, file);
        await SaveToFile(Path.Combine(outputPath.FullName, "plan.json"), JsonSerializer.Serialize(plan));

        var implementationTasks = plan.steps.SelectMany(
            (step) => step.subtasks.Select(
                async (subtask) => {
                        var implementationResult = await CallFunction<string>(nameof(Developer), Developer.Implement, subtask.LLM_prompt);
                        await sandboxSkill.RunInDotnetAlpineAsync(implementationResult);
                        await SaveToFile(Path.Combine(outputPath.FullName, $"{step.step}-{subtask.subtask}.sh"), implementationResult);
                        return implementationResult; }));
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
        var variables = new[]
        {
            new { key = "input", value = input }
        };

        var requestBody = new { variables };
        var requestBodyJson = JsonSerializer.Serialize(requestBody);

        Console.WriteLine($"Calling skill '{skillName}' function '{functionName}' with input '{input}'");
        Console.WriteLine(requestBodyJson);

        using var httpClient = new HttpClient();
        var apiUrl = $"http://localhost:7071/api/skills/{skillName}/functions/{functionName}";
        var response = await httpClient.PostAsync(apiUrl, new StringContent(requestBodyJson));

        if (!response.IsSuccessStatusCode)
        {
            Console.WriteLine($"Error: {response.StatusCode} - {response.ReasonPhrase}");
            return default;
        }

        var responseJson = await response.Content.ReadAsStringAsync();
        
        var skillResponse = JsonSerializer.Deserialize<SkillsResponse>(responseJson);
        var result = typeof(T) != typeof(string) ? JsonSerializer.Deserialize<T>(skillResponse.Response) : (T)(object)skillResponse.Response;
        
        Console.WriteLine(responseJson);
        return result;
    }
}

public static class PM { public static string Readme = "Readme"; public static string BootstrapProject = "BootstrapProject"; }
public static class DevLead { public static string Plan="Plan"; }
public static class Developer { public static string Implement="Implement"; }