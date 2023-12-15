// Copyright (c) Microsoft Corporation. All rights reserved.
// Example04_Dynamic_GroupChat_Get_MLNET_PR.cs

using AgentChat.DotnetInteractiveService;
using AutoGen;
using AutoGen.Extension;
using FluentAssertions;
using autogen = AutoGen.API;
using GroupChat = AutoGen.GroupChat;
using GroupChatExtension = AutoGen.GroupChatExtension;
using IAgent = AutoGen.IAgent;
using Message = AutoGen.Message;

public class Example04_Dynamic_GroupChat_Get_MLNET_PR
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
            systemMessage: @"You act as group admin that lead other agents to resolve task together. DON'T WRITE CODE. Here's the workflow you follow:
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
                if (msgs.Where(m => m.From == "admin").LastOrDefault()?.Content.Contains("TERMINATE") ?? false)
                {
                    // terminate the conversation
                    return new Message(Role.Assistant, GroupChatExtension.TERMINATE);
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
                { dotnetInteractiveFunctions.InstallNugetPackagesFunction.Name, dotnetInteractiveFunctions.InstallNugetPackagesWrapper },
            }).RegisterReply(async (msgs, ct) =>
            {
                // retrieve code from the last message
                // if the last message is not from coder, ask coder to write code
                var lastMessage = msgs.Last();
                if (lastMessage.From != "coder")
                {
                    return new Message(Role.Assistant, "coder, write code please");
                }

                // if the last message is from coder, retrieve the code between ```csharp and ```
                var code = lastMessage.Content;
                var codeStartIndex = code.IndexOf("```csharp");
                var codeEndIndex = code.IndexOf("```", codeStartIndex + 1);
                if (codeStartIndex < 0 || codeEndIndex < 0)
                {
                    return null;
                }
                else
                {
                    // refuse to run code that has Main() function
                    if (code.Contains("Main") && code.Contains("Program"))
                    {
                        return new Message(Role.Assistant, "I refuse to run code that has Main() function. Please convert it to top-level statement");
                    }
                    else
                    {
                        code = code.Substring(codeStartIndex + 9, codeEndIndex - codeStartIndex - 9);
                        // run code
                        var runCodeResult = await dotnetInteractiveFunctions.RunCode(code);

                        return new Message(Role.Assistant, runCodeResult);
                    }
                }
            });

        // create group chat
        var groupChat = new GroupChat(
            admin: admin,
            agents: new IAgent[] { coder, runner });

        admin.AddInitializeMessage("Welcome to the group chat! Work together to resolve my task.", groupChat);
        coder.AddInitializeMessage("Hey I'm Coder, I write dotnet code.", groupChat);
        runner.AddInitializeMessage("Hey I'm Runner, I run dotnet code from coder.", groupChat);
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
        var maxRound = 40;
        IEnumerable<Message> conversationHistory = new List<Message>()
        {
            new Message(Role.Assistant, "the number of resolved step is 0")
            {
                From = admin.Name,
            },
        };

        while (maxRound > 0)
        {
            conversationHistory = await admin.SendAsync(
                receiver: groupChatManager,
                conversationHistory,
                maxRound: 1);

            // print out the last message
            Console.WriteLine(conversationHistory.Last().FormatMessage());

            // check if the last message is TERMINATE
            if (conversationHistory.Last().IsGroupChatTerminateMessage())
            {
                break;
            }

            maxRound--;
        }

        // check if pr.txt exist in work dir
        var prFile = Path.Combine(workDir, "pr.txt");
        File.Exists(prFile).Should().BeTrue();
    }
}
