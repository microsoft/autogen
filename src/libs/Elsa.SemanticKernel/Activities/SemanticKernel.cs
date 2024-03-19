using Elsa.Extensions;
using JetBrains.Annotations;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;

using System;
using System.Text;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using Microsoft.AI.DevTeam.Skills;
using Elsa.Workflows;
using Elsa.Workflows.Attributes;
using Elsa.Workflows.UIHints;
using Elsa.Workflows.Models;
using Azure.AI.OpenAI;
using Azure;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Http.Resilience;
using Microsoft.SemanticKernel.Connectors.OpenAI;


namespace Elsa.SemanticKernel;

/// <summary>
/// Invoke a Semantic Kernel skill.
/// </summary>
[Activity("Elsa", "Semantic Kernel", "Invoke a Semantic Kernel skill. ", DisplayName = "Generic Semantic Kernel Skill", Kind = ActivityKind.Task)]
[PublicAPI]
public class SemanticKernelSkill : CodeActivity<string>
{
    [Input(
    Description = "System Prompt",
    UIHint = InputUIHints.MultiLine,
    DefaultValue = PromptDefaults.SystemPrompt)]
    public Input<string> SysPrompt { get; set; } = default!;

    [Input(
    Description = "User Input Prompt",
    UIHint = InputUIHints.MultiLine,
    DefaultValue = PromptDefaults.UserPrompt)]
    public Input<string> Prompt { get; set; }

    [Input(
    Description = "Max retries",
    UIHint = InputUIHints.SingleLine,
    DefaultValue = KernelSettings.DefaultMaxRetries)]
    public Input<int> MaxRetries { get; set; }

    [Input(
    Description = "The skill to invoke from the semantic kernel",
    UIHint = InputUIHints.SingleLine,
    DefaultValue = "Chat")]
    public Input<string> SkillName { get; set; }

    [Input(
    Description = "The function to invoke from the skill",
    UIHint = InputUIHints.SingleLine,
    DefaultValue = "ChatCompletion")]
    public Input<string> FunctionName { get; set; }

    /*     [Input(
            Description = "Mockup - don't actually call the AI, just output the prompts",
            UIHint = InputUIHints.Checkbox,
            DefaultValue = false)]
        public Input<bool> Mockup { get; set; } */

    /// <inheritdoc />
    protected override async ValueTask ExecuteAsync(ActivityExecutionContext workflowContext)
    {
        var test = SkillName.Get(workflowContext);
        var skillName = SkillName.Get(workflowContext);
        var functionName = FunctionName.Get(workflowContext);
        var systemPrompt = SysPrompt.Get(workflowContext);
        var maxRetries = MaxRetries.Get(workflowContext);
        var prompt = Prompt.Get(workflowContext);
        //var mockup = Mockup.Get(workflowContext);
        var mockup = false;

        string info = ($"#################\nSkill: {skillName}\nFunction: {functionName}\nPrompt: {prompt}\n#################\n\n");

        if (mockup)
        {
            workflowContext.SetResult(info);
        }
        else
        {
            // get the kernel
            var kernel = KernelBuilder();

            // load the skill
            var promptTemplate = Skills.ForSkillAndFunction(skillName, functionName);

            var function = kernel.CreateFunctionFromPrompt(promptTemplate, new OpenAIPromptExecutionSettings { MaxTokens = 8000, Temperature = 0.4, TopP = 1 });

            // set the context (our prompt)
            var arguments =  new KernelArguments{
                ["input"] = prompt
            };

            var answer = await kernel.InvokeAsync(function, arguments);
            workflowContext.SetResult(answer);
        }
    }

    /// <summary>
    /// Load the skills into the kernel
    /// </summary>
    private string ListSkillsInKernel(Kernel kernel)
    {

        var theSkills = LoadSkillsFromAssemblyAsync("skills", kernel);
        var functionsAvailable = kernel.Plugins.GetFunctionsMetadata();

        var list = new StringBuilder();
        foreach (var function in functionsAvailable)
        {
            Console.WriteLine($"Skill: {function.PluginName}");
            
                // Function description
                if (function.Description != null)
                {
                    list.AppendLine($"// {function.Description}");
                }
                else
                {
                    Console.WriteLine("{0}.{1} is missing a description", function.PluginName, function.Name);
                    list.AppendLine($"// Function {function.PluginName}.{function.Name}.");
                }

                // Function name
                list.AppendLine($"{function.PluginName}.{function.Name}");

                // Function parameters
                foreach (var p in function.Parameters)
                {
                    var description = string.IsNullOrEmpty(p.Description) ? p.Name : p.Description;
                    var defaultValueString =  p.DefaultValue == null ? string.Empty : $" (default value: {p.DefaultValue})";
                    list.AppendLine($"Parameter \"{p.Name}\": {description} {defaultValueString}");
                }
        }

        Console.WriteLine($"List of all skills ----- {list.ToString()}");
        return list.ToString();
    }

    /// <summary>
    /// Gets a semantic kernel instance
    /// </summary>
    /// <returns>Microsoft.SemanticKernel.IKernel</returns>
    private Kernel KernelBuilder()
    {
        var kernelSettings = KernelSettings.LoadSettings();

        var clientOptions = new OpenAIClientOptions();
        clientOptions.Retry.NetworkTimeout = TimeSpan.FromMinutes(5);
        var openAIClient = new OpenAIClient(new Uri(kernelSettings.Endpoint), new AzureKeyCredential(kernelSettings.ApiKey), clientOptions);
        var builder = Kernel.CreateBuilder();
        builder.Services.AddLogging( c=> c.AddConsole().AddDebug().SetMinimumLevel(LogLevel.Debug));
        builder.Services.AddAzureOpenAIChatCompletion(kernelSettings.DeploymentOrModelId, openAIClient);
        builder.Services.ConfigureHttpClientDefaults(c=>
        {
            c.AddStandardResilienceHandler().Configure( o=> {
                o.Retry.MaxRetryAttempts = 5;
                o.Retry.BackoffType = Polly.DelayBackoffType.Exponential;
            });
        });
        return builder.Build();
    }

    ///<summary>
    /// Gets a list of the skills in the assembly
    ///</summary>
    private IEnumerable<string> LoadSkillsFromAssemblyAsync(string assemblyName, Kernel kernel)
    {
        var skills = new List<string>();
        var assembly = Assembly.Load(assemblyName);
        Type[] skillTypes = assembly.GetTypes().ToArray();
        foreach (Type skillType in skillTypes)
        {
            if (skillType.Namespace.Equals("Microsoft.SKDevTeam"))
            {
                skills.Add(skillType.Name);
                var functions = skillType.GetFields();
                foreach (var function in functions)
                {
                    string field = function.FieldType.ToString();
                    if (field.Equals("Microsoft.SKDevTeam.SemanticFunctionConfig"))
                    {
                        var prompt = Skills.ForSkillAndFunction(skillType.Name, function.Name);
                        var skfunc = kernel.CreateFunctionFromPrompt(
                            prompt, new OpenAIPromptExecutionSettings { MaxTokens = 8000, Temperature = 0.4, TopP = 1 });

                        Console.WriteLine($"SK Added function: {skfunc.Metadata.PluginName}.{skfunc.Metadata.Name}");
                    }
                }
            }
        }
        return skills;
    }
}