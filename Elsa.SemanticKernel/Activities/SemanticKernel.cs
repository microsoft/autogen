using Elsa.Extensions;
using Elsa.Workflows.Core;
using Elsa.Workflows.Core.Attributes;
using Elsa.Workflows.Core.Models;
using JetBrains.Annotations;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.Memory.Qdrant;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.TextEmbedding;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Microsoft.SemanticKernel.Reliability;
namespace Elsa.SemanticKernel;
using System;
using System.Text.Json;
using System.Threading.Tasks;
using skills;

/// <summary>
/// Invoke a Semantic Kernel skill.
/// </summary>
[Activity("Elsa", "AI Chat", "Invoke a Semantic Kernel skill. ", DisplayName = "Semantic Kernel Skill", Kind = ActivityKind.Task)]
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
    DefaultValue = 9)]
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

    /// <inheritdoc />
    protected override async ValueTask ExecuteAsync(ActivityExecutionContext workflowContext)
    {
        var test = SkillName.Get(workflowContext);
        var skillName = SkillName.Get(workflowContext);
        var functionName = FunctionName.Get(workflowContext);
        var systemPrompt = SysPrompt.Get(workflowContext);
        var maxRetries = MaxRetries.Get(workflowContext);
        var prompt = Prompt.Get(workflowContext);
        var kernelSettings = KernelSettings.LoadSettings();
        var kernelConfig = new KernelConfig();

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
    .SetMinimumLevel(kernelSettings.LogLevel ?? LogLevel.Warning);
        });
        /* var memoryStore = new QdrantMemoryStore(new QdrantVectorDbClient("http://qdrant", 1536, port: 6333));
        var embedingGeneration = new AzureTextEmbeddingGeneration(kernelSettings.EmbeddingDeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey);
        var semanticTextMemory = new SemanticTextMemory(memoryStore, embedingGeneration);
 */
        var kernel = new KernelBuilder()
        .WithLogger(loggerFactory.CreateLogger<IKernel>())
        .WithAzureChatCompletionService(kernelSettings.DeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey, true, kernelSettings.ServiceId, true)
        //.WithMemory(semanticTextMemory)
        .WithConfiguration(kernelConfig)
        .Configure(c => c.SetDefaultHttpRetryConfig(new HttpRetryConfig
        {
            MaxRetryCount = maxRetries,
            UseExponentialBackoff = true,
            // MinRetryDelay = TimeSpan.FromSeconds(2),
            // MaxRetryDelay = TimeSpan.FromSeconds(8),
            MaxTotalRetryTime = TimeSpan.FromSeconds(300),
            // RetryableStatusCodes = new[] { HttpStatusCode.TooManyRequests, HttpStatusCode.RequestTimeout },
            // RetryableExceptions = new[] { typeof(HttpRequestException) }
        }))
        .Build();

/*         var interestingMemories = kernel.Memory.SearchAsync("ImportedMemories", prompt, 2);
        var wafContext = "Consider the following contextual snippets:";
        await foreach (var memory in interestingMemories)
        {
            wafContext += $"\n {memory.Metadata.Text}";
        } */

        var skillConfig = SemanticFunctionConfig.ForSkillAndFunction(skillName, functionName);
        var function = kernel.CreateSemanticFunction(skillConfig.PromptTemplate, skillConfig.Name, skillConfig.SkillName,
        skillConfig.Description, skillConfig.MaxTokens, skillConfig.Temperature,
        skillConfig.TopP, skillConfig.PPenalty, skillConfig.FPenalty);

        var context = new ContextVariables();
        context.Set("input", prompt);
        //context.Set("wafContext", wafContext);

        var answer = await kernel.RunAsync(context, function).ConfigureAwait(false);
        //debug output to console
        Console.WriteLine($"Skill: {skillName} Function: {functionName} Prompt: {prompt} Answer: {answer}");
        workflowContext.SetResult(answer);
    }
}