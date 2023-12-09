// Copyright (c) Microsoft Corporation. All rights reserved.
// Example04_Dynamic_GroupChat.cs

using AgentChat.DotnetInteractiveService;
using AutoGen;
using AutoGen.Extension;
using FluentAssertions;
using Microsoft.SemanticKernel.AI.ChatCompletion;
using autogen = AutoGen.API;

public static class Example04_Dynamic_GroupChat_Get_MLNET_PR
{
    public static async Task RunAsync()
    {
        // setup dotnet interactive
        var workDir = Path.Combine(Path.GetTempPath(), "InteractiveService");
        if (!Directory.Exists(workDir))
            Directory.CreateDirectory(workDir);

        var service = new InteractiveService(workDir);
        var dotnetInteractiveFunctions = new DotnetInteractiveFunction(service);
        await service.StartAsync(workDir, default);

        // get OpenAI Key and create config
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var gpt3Config = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-3.5-turbo" });
        var gpt4Config = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-4-1106-preview" });

        // create admin agent
        var adminConfig = new AssistantAgentConfig
        {
            Temperature = 0,
            ConfigList = gpt3Config,
        };
        var admin = new AssistantAgent(
            name: "admin",
            systemMessage: @"You act as group admin that lead other agents to resolve task together. Here's the workflow you follow:
-workflow-
if all_steps_are_resolved
    say [TERMINATE]
else
    resolve_step
-end-

The task is
Retrieve the latest PR from mlnet repo, print the result and save the result to pr.txt.
The steps to resolve the task are:
1. Send a GET request to the GitHub API to retrieve the list of pull requests for the mlnet repo.
2. Parse the response JSON to extract the latest pull request.
3. Print the result to the console and save the result to a file named ""pr.txt"".

Here are some examples for resolve_step:
- The step to resolve is xxx, let's work on this step.",
            llmConfig: adminConfig)
            .RegisterReply(async (msgs, ct) =>
            {
                if (msgs.Where(m => m.From == "admin").Last().Content.Contains("TERMINATE"))
                {
                    // terminate the conversation
                    return new Message(AuthorRole.Assistant, GroupChatExtension.TERMINATE);
                }

                return null;
            });

        // create coder agent
        var coderConfig = new AssistantAgentConfig
        {
            Temperature = 0,
            ConfigList = gpt4Config,
        };
        var coder = new AssistantAgent(
            name: "coder",
            systemMessage: @"You act as dotnet coder, you write dotnet script to resolve task.
-workflow-
write_code_to_resolve_coding_task

if code_has_error
    fix_code_error

if task_complete, say [COMPLETE]

-end-

Here're some rules to follow on write_code_to_resolve_current_step:
- put code between ```csharp and ```
- Use top-level statements, remove main function, just write code, like what python does.
- Remove all `using` statement. Runner can't handle it.
- Try to use `var` instead of explicit type.
- Try avoid using external library.
- Don't use external data source, like file, database, etc. Create a dummy dataset if you need.
- Always print out the result to console. Don't write code that doesn't print out anything.

Here are some examples for write_code_to_resolve_coding_task:
```nuget
xxx
```
```csharp
xxx
```

Here are some examples for fix_code_error:
The error is caused by xxx. Here's the fix code
```csharp
xxx
```",
            llmConfig: coderConfig);

        // create runner agent
        var runnerConfig = new AssistantAgentConfig
        {
            Temperature = 0,
            ConfigList = gpt3Config,
            FunctionDefinitions = new[]
            {
                dotnetInteractiveFunctions.RunCodeFunction,
                dotnetInteractiveFunctions.InstallNugetPackagesFunction,
            },
        };
        var runner = new AssistantAgent(
            name: "runner",
            systemMessage: @"you act as dotnet runner, you run dotnet script and install nuget packages. Here's the workflow you follow:
-workflow-
if code_is_available
    call run_code

if nuget_packages_is_available
    call install_nuget_packages

for any other case
    say [NO_CODE_AVAILABLE]
-end-",
            llmConfig: runnerConfig,
            defaultReply: "NO_CODE_AVAILABLE",
            functionMap: new Dictionary<string, Func<string, Task<string>>>()
            {
                { dotnetInteractiveFunctions.RunCodeFunction.Name, dotnetInteractiveFunctions.RunCodeWrapper},
                { dotnetInteractiveFunctions.InstallNugetPackagesFunction.Name, dotnetInteractiveFunctions.InstallNugetPackagesWrapper },
            }).RegisterReply(async (msgs, ct) =>
            {
                if (msgs.Where(m => m.From == "coder").Last().Content is string code && code.Contains("```csharp") && code.Contains("Main") && code.Contains("Program"))
                {
                    // refuse to run code that has Main() function
                    return new Message(AuthorRole.Assistant, "I refuse to run code that has Main() function. Please convert it to top-level statement");
                }

                return null;
            });

        // create group chat
        var groupChat = new GroupChat(
            admin: admin,
            agents: new IAgent[] { coder, runner });

        admin.AddInitializeMessage("Welcome to the group chat! Work together to resolve my task.", groupChat);
        coder.AddInitializeMessage("Hey I'm Coder", groupChat);
        runner.AddInitializeMessage("Hey I'm Runner", groupChat);
        admin.AddInitializeMessage($"The link to mlnet repo is: https://github.com/dotnet/machinelearning. you don't need a token to use github pr api. Make sure to include a User-Agent header, otherwise github will reject it.", groupChat);
        admin.AddInitializeMessage(@$"Here's the workflow for this group chat
-groupchat workflow-
if all_steps_are_resolved
    admin_terminate_chat
else

admin_give_step_to_resolve
coder_write_code_to_resolve_step
runner_run_code_from_coder
if code_is_correct
    admin_give_next_step
else
    coder_fix_code_error
", groupChat);

        // start group chat
        var groupChatManager = new GroupChatManager(groupChat);
        var conversation = await admin.SendAsync(
            receiver: groupChatManager,
            message: "Here's the first step to resolve the task: Send a GET request to the GitHub API to retrieve the list of pull requests for the mlnet repo.",
            maxRound: 100);

        // print out the conversation
        foreach (var msg in conversation)
        {
            Console.WriteLine(msg.FormatMessage());
        }

        // check if pr.txt exist in work dir
        var prFile = Path.Combine(workDir, "pr.txt");
        File.Exists(prFile).Should().BeTrue();
    }
}
