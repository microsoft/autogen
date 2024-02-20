// Copyright (c) Microsoft Corporation. All rights reserved.
// Example04_Dynamic_GroupChat_Get_MLNET_PR.cs

using System.Text;
using System.Text.Json;
using AutoGen;
using AutoGen.DotnetInteractive;
using FluentAssertions;
using autogen = AutoGen.LLMConfigAPI;
using GroupChat = AutoGen.GroupChat;
using GroupChatExtension = AutoGen.GroupChatExtension;
using IAgent = AutoGen.IAgent;
using Message = AutoGen.Message;

public partial class Example04_Dynamic_GroupChat_Get_MLNET_PR
{
    /// <summary>
    /// Save the most recent code block and its output to context
    /// </summary>
    /// <param name="codeBlock">code block</param>
    /// <param name="codeOutput">code output</param>
    [Function]
    public async Task<string> SaveContext(string codeBlock, string codeOutput)
    {
        return $@"// IGNORE THIS LINE [CODE_SOLUTION]
The existing code solution is:
{codeBlock}

The output of the code is:
{codeOutput}";
    }

    struct CodeReviewResult
    {
        public bool HasMultipleCodeBlocks { get; set; }
        public bool HasNugetPackages { get; set; }
        public bool IsTopLevelStatement { get; set; }
        public bool IsDotnetCodeBlock { get; set; }
    }

    struct StepProgressReviewResult
    {
        public bool IsCodeSolutionAvailable { get; set; }

        public bool IsLatestCodeSolutionHasBeenRun { get; set; }

        public bool IsCodeSolutionRunSuccessfully { get; set; }
    }

    [Function]
    public async Task<string> ReviewCurrentStepProgress(
        bool isCodeSolutionAvailable,
        bool isLatestCodeSolutionHasBeenRun,
        bool isCodeSolutionRunSuccessfully)
    {
        var obj = new StepProgressReviewResult
        {
            IsCodeSolutionAvailable = isCodeSolutionAvailable,
            IsLatestCodeSolutionHasBeenRun = isLatestCodeSolutionHasBeenRun,
            IsCodeSolutionRunSuccessfully = isCodeSolutionRunSuccessfully,
        };

        return JsonSerializer.Serialize(obj);
    }


    /// <summary>
    /// review code block
    /// </summary>
    /// <param name="hasMultipleCodeBlocks">true if there're multipe csharp code blocks</param>
    /// <param name="hasNugetPackages">true if there's nuget package to install</param>
    /// <param name="isTopLevelStatement">true if the code is in top level statement</param>
    /// <param name="isDotnetCodeBlock">true if the code block is csharp code block</param>
    [Function]
    public async Task<string> ReviewCodeBlock(
        bool hasMultipleCodeBlocks,
        bool hasNugetPackages,
        bool isTopLevelStatement,
        bool isDotnetCodeBlock)
    {
        var obj = new CodeReviewResult
        {
            HasMultipleCodeBlocks = hasMultipleCodeBlocks,
            HasNugetPackages = hasNugetPackages,
            IsTopLevelStatement = isTopLevelStatement,
            IsDotnetCodeBlock = isDotnetCodeBlock,
        };

        return JsonSerializer.Serialize(obj);
    }

    public static async Task RunAsync()
    {
        var instance = new Example04_Dynamic_GroupChat_Get_MLNET_PR();

        // setup dotnet interactive
        var workDir = Path.Combine(Path.GetTempPath(), "InteractiveService");
        if (!Directory.Exists(workDir))
            Directory.CreateDirectory(workDir);

        var service = new InteractiveService(workDir);
        var dotnetInteractiveFunctions = new DotnetInteractiveFunction(service);

        var prFile = Path.Combine(workDir, "pr.txt");
        if (File.Exists(prFile))
            File.Delete(prFile);

        await service.StartAsync(workDir, default);

        // get OpenAI Key and create config
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var gptConfig = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-3.5-turbo" });

        var steps = new[]
        {
            "Send a GET request to the GitHub API to retrieve the list of pull requests for the mlnet repo.",
            "Parse the response JSON to extract the latest pull request.",
            "Print the result to the console and save the result to a file named \"pr.txt\".",
        };

        // Create admin agent
        // When resolving the current step, admin will review the progress of current step.
        // If the code solution is not available, admin will ask coder to write code.
        // If the code solution is available but not run, admin will ask runner to run the code.
        // If the code solution is available and run, admin will check if the code run is successful.
        // If the code run is successful, admin will terminate the conversation. Otherwise, admin will ask coder to fix the code and repeat the process.
        var admin = new AssistantAgent(
            name: "admin",
            systemMessage: @"You are admin, you review the progress of current step.",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gptConfig,
                FunctionDefinitions = new[]
                {
                    instance.ReviewCurrentStepProgressFunction,
                },
            },
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { nameof(ReviewCurrentStepProgress), instance.ReviewCurrentStepProgressWrapper },
            })
            .RegisterPostProcess(async (_, reply, ct) =>
            {
                if (reply.FunctionName != nameof(ReviewCurrentStepProgress))
                {
                    return reply;
                }
                var reviewResult = JsonSerializer.Deserialize<StepProgressReviewResult>(reply.Content!);
                if (reviewResult.IsCodeSolutionAvailable is false)
                {
                    return new Message(Role.Assistant, "coder, write code please");
                }

                if (reviewResult.IsCodeSolutionRunSuccessfully is false)
                {
                    return new Message(Role.Assistant, "coder, fix the code please");
                }

                if (reviewResult.IsLatestCodeSolutionHasBeenRun is false)
                {
                    return new Message(Role.Assistant, "runner, run the code please");
                }

                return new Message(Role.Assistant, GroupChatExtension.TERMINATE);
            })
            .RegisterPrintFormatMessageHook();

        // create context manage agent
        // context manager create context for current step and collect code block and its output when a step is resolved.
        var contextManagerAgent = new AssistantAgent(
            name: "context_manager",
            systemMessage: @"You are context manager, you collect information from conversation context",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gptConfig,
                FunctionDefinitions = new[]
                {
                    instance.SaveContextFunction,
                },
            },
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { nameof(SaveContext), instance.SaveContextWrapper },
            })
            .RegisterPrintFormatMessageHook();

        // create coder agent
        // The coder agent is a composite agent that contains dotnet coder, code reviewer and nuget agent.
        // The dotnet coder write dotnet code to resolve the task.
        // The code reviewer review the code block from coder's reply.
        // The nuget agent install nuget packages if there's any.
        var dotnetCoder = new AssistantAgent(
            name: "coder",
            systemMessage: @"You act as dotnet coder, you write dotnet code to resolve task. Once you finish writing code, ask runner to run the code for you.

Here're some rules to follow on writing dotnet code:
- put code between ```csharp and ```
- When creating http client, use `var httpClient = new HttpClient()`. Don't use `using var httpClient = new HttpClient()` because it will cause error when running the code.
- Try to use `var` instead of explicit type.
- Try avoid using external library, use .NET Core library instead.
- Use top level statement to write code.
- Always print out the result to console. Don't write code that doesn't print out anything.

If you need to install nuget packages, put nuget packages in the following format:
```nuget
nuget_package_name
```

If your code is incorrect, runner will tell you the error message. Fix the error and send the code again.

Here's some externel information
- The link to mlnet repo is: https://github.com/dotnet/machinelearning. you don't need a token to use github pr api. Make sure to include a User-Agent header, otherwise github will reject it.
",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0.4f,
                ConfigList = gptConfig,
            })
            .RegisterPrintFormatMessageHook();

        // code reviewer agent will review if code block from coder's reply satisfy the following conditions:
        // - There's only one code block
        // - The code block is csharp code block
        // - The code block is top level statement
        // - The code block is not using declaration
        var codeReviewAgent = new AssistantAgent(
            name: "code_reviewer",
            systemMessage: @"You review code block from coder",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gptConfig,
                FunctionDefinitions = new[]
                {
                    instance.ReviewCodeBlockFunction,
                },
            },
            functionMap: new Dictionary<string, Func<string, Task<string>>>()
            {
                { nameof(ReviewCodeBlock), instance.ReviewCodeBlockWrapper },
            })
            .RegisterPrintFormatMessageHook();

        // nuget agent will install nuget packages if there's any.
        var nugetAgent = new AssistantAgent(
           name: "nuget",
           systemMessage: @"Install nuget packages if there's any, otherwise say [NO_NUGET_PACKAGE]",
           llmConfig: new ConversableAgentConfig
           {
               Temperature = 0,
               ConfigList = gptConfig,
               FunctionDefinitions = new[]
               {
                    dotnetInteractiveFunctions.InstallNugetPackagesFunction,
               },
           },
           functionMap: new Dictionary<string, Func<string, Task<string>>>()
           {
                { dotnetInteractiveFunctions.InstallNugetPackagesFunction.Name, dotnetInteractiveFunctions.InstallNugetPackagesWrapper },
           })
           .RegisterPrintFormatMessageHook();

        // composite dotnet coder agent, codeReviewAgent and nuget agent together using PostProcessHook
        var coder = dotnetCoder.RegisterPostProcess(async (conversation, reply, ct) =>
        {
            // review code process
            // This process will repeat until the code block satisfy the following conditions:
            var maxRetry = 5;
            while (maxRetry-- > 0)
            {
                var prompt = $@"You are a code reviewer who reviews code from coder. Below is the most recent reply from coder:

### coder's reply ###
{reply.Content}
### end of coder's reply ###

please carefully review the code block from coder and provide feedback.";
                var reviewResult = await codeReviewAgent.SendAsync(prompt);

                var reviewResultObj = JsonSerializer.Deserialize<CodeReviewResult>(reviewResult.Content!);
                var reviews = new List<string>();
                if (reviewResultObj.HasMultipleCodeBlocks)
                {
                    var fixCodeBlockPrompt = @"There're multiple code blocks, please combine them into one code block";
                    reviews.Add(fixCodeBlockPrompt);
                }

                if (reviewResultObj.IsDotnetCodeBlock is false)
                {
                    var fixCodeBlockPrompt = @"The code block is not csharp code block, please write dotnet code only";
                    reviews.Add(fixCodeBlockPrompt);
                }

                if (reviewResultObj.IsTopLevelStatement is false)
                {
                    var fixCodeBlockPrompt = @"The code is not top level statement, please rewrite your dotnet code using top level statement";
                    reviews.Add(fixCodeBlockPrompt);
                }

                if (reviews.Count > 0)
                {
                    var sb = new StringBuilder();
                    sb.AppendLine(@$"### code ###
{reply.Content}
### End of code ###");
                    sb.AppendLine("There're some comments from code reviewer, please fix these comments");
                    foreach (var review in reviews)
                    {
                        sb.AppendLine($"- {review}");
                    }

                    reply = await dotnetCoder.SendAsync(sb.ToString());
                    continue;
                }

                if (reviewResultObj.HasNugetPackages)
                {
                    var installNugetPrompt = @"There're nuget packages to install, please install them";
                    var installNugetMessage = new Message(Role.User, installNugetPrompt);
                    var chatHistory = new List<Message>
                    {
                        installNugetMessage,
                        reply,
                    };
                    await nugetAgent.SendAsync(chatHistory: chatHistory);
                }

                return reply;
            }

            throw new Exception("Max retry reached, please fix the code and try again");
        });

        // create runner agent
        // The runner agent will run the code block from coder's reply.
        // It runs dotnet code using dotnet interactive service hook.
        // It also truncate the output if the output is too long.
        var runner = new AssistantAgent(
            name: "runner",
            defaultReply: "No code available, coder, write code please",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gptConfig,
            })
            .RegisterDotnetCodeBlockExectionHook(interactiveService: service)
            .RegisterPostProcess(async (_, reply, _) =>
            {
                if (reply.Content is { Length: > 400 })
                {
                    reply.Content = reply.Content.Substring(0, 200) + "...(too long to be printed)";
                }

                return reply;
            })
            .RegisterPrintFormatMessageHook();

        // create group chat
        var groupChat = new GroupChat(
            admin: admin,
            members: new IAgent[] { coder, runner });

        admin.AddInitializeMessage("Welcome to the group chat! Work together to resolve my task.", groupChat);
        coder.AddInitializeMessage("Hey I'm Coder, I write dotnet code.", groupChat);
        runner.AddInitializeMessage("Hey I'm Runner, I run dotnet code from coder.", groupChat);

        // start group chat
        var groupChatManager = new GroupChatManager(groupChat);
        var previousContext = "No previous context";
        foreach (var step in steps)
        {
            var createContextForCurrentStepPrompt = @$"Create context for current step
previous context: {previousContext}

current step to resolve: {step}";

            Console.WriteLine(createContextForCurrentStepPrompt);

            IEnumerable<Message> chatHistoryForCurrentStep = new[]
            {
                new Message(Role.Assistant, createContextForCurrentStepPrompt)
                {
                    From = "admin",
                },
            };
            chatHistoryForCurrentStep = await admin.SendAsync(groupChatManager, chatHistoryForCurrentStep, maxRound: 20);
            var previousContextMessage = await contextManagerAgent.SendAsync(message: "Save context from conversation above", chatHistory: chatHistoryForCurrentStep);
            previousContext = previousContextMessage.Content;
        }

        File.Exists(prFile).Should().BeTrue();
    }
}
