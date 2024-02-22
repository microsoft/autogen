// Copyright (c) Microsoft Corporation. All rights reserved.
// Example04_Dynamic_GroupChat_Get_MLNET_PR.cs

using System.Text;
using System.Text.Json;
using AutoGen;
using AutoGen.DotnetInteractive;
using FluentAssertions;
using autogen = AutoGen.LLMConfigAPI;
using GroupChat = AutoGen.GroupChat;
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

        var helperAgent = new AssistantAgent(
            name: "helper",
            systemMessage: "You are a helpful AI assistant",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gptConfig,
            })
            .RegisterPrintFormatMessageHook();

        var userProxy = new UserProxyAgent(name: "user")
            .RegisterPrintFormatMessageHook();

        // Create admin agent
        var admin = new AssistantAgent(
            name: "admin",
            systemMessage: """
            You are a manager who takes coding task from user and resolve tasks by splitting them into steps and assign each step to different agents.
            Here's available agents who you can assign task to:
            - coder: write dotnet code to resolve task
            - runner: run dotnet code from coder
            - reviewer: review code from coder

            You can use the following json format to assign task to agents:
            ```task
            {
                "to": "{agent_name}",
                "task": "{a short description of the task}",
                "context": "{previous context from scratchpad}"
            }
            ```

            If you need to ask user for extra information, you can use the following format:
            ```ask
            {
                "question": "{question}"
            }
            ```

            The conversation might be very long so it will be helpful to note down the summary of each step to your scratchpad once it's resolved. You can use the following json format to write down the note:
            ```scratchpad
            // anything you want to note down
            ```
            Once the task is resolved, summarize each steps and results and send the summary to the user using the following format:
            ```summary
            {
                "task": "{task}",
                "steps": [
                    {
                        "step": "{step}",
                        "result": "{result}"
                    }
                ]
            }
            ```

            Your reply must contain one of [task|ask|summary] to indicate the type of your message. You can use scratchpad as many times as you want.
            """,
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gptConfig,
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
            systemMessage: """
            You are a code reviewer who reviews code from coder. You need to check if the code satisfy the following conditions:
            - There's only one code block
            - The code block is csharp code block
            - The code block is top level statement
            - The code block is not using declaration when creating http client

            Put your comment between ```review and ```, if the code satisfies all conditions, writes APPROVED in result. Otherwise, put REJECTED along with comments. make sure your comment is clear and easy to understand.
            
            e.g.
            ```review
            result: [APPROVED|REJECTED]
            comment: [your comment]
            ```
            """,
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gptConfig,
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
            .RegisterMiddleware(async (msgs, option, agent, ct) =>
            {
                var mostRecentCoderMessage = msgs.LastOrDefault(x => x.From == "coder") ?? throw new Exception("No coder message found");
                return await agent.GenerateReplyAsync(new[] { mostRecentCoderMessage }, option, ct);
            })
            .RegisterPrintFormatMessageHook();

        var adminToCoderTransition = Transition.Create(admin, dotnetCoder, async (from, to, messages) =>
        {
            // the last message should be from admin
            var lastMessage = messages.Last();
            if (lastMessage.From != admin.Name)
            {
                return false;
            }

            // check if the last admin message create a task for coder
            var prompt = $@"Please determine if admin's message creates a task to coder,
If the message contains a task for coder, says: true, the task for coder is xx
Otherwise, says: false, the message doesn't contain a task for coder

### admin's message ###
{lastMessage.Content}";

            var result = await helperAgent.SendAsync(prompt);

            return result.Content.ToLower().Contains("true");
        });
        var coderToAdminTransition = Transition.Create(dotnetCoder, admin);
        var adminToRunnerTransition = Transition.Create(admin, runner, async (from, to, messages) =>
        {
            // the last message should be from admin
            var lastMessage = messages.Last();
            if (lastMessage.From != admin.Name)
            {
                return false;
            }

            // check if the last admin message create a task for runner
            var prompt = $@"Please determine if admin's message creates a task for runner.

If the message contains a task for runner, says: true, the task for runner is xx
otherwise, says: false, the message doesn't contain a task for runner
### admin's message ###
{lastMessage.Content}";

            var result = await helperAgent.SendAsync(prompt);

            return result.Content.ToLower().Contains("true");
        });

        var runnerToAdminTransition = Transition.Create(runner, admin);

        var adminToReviewerTransition = Transition.Create(admin, codeReviewAgent, async (from, to, messages) =>
        {
            // the last message should be from admin
            var lastMessage = messages.Last();
            if (lastMessage.From != admin.Name)
            {
                return false;
            }

            // check if the last admin message create a task for code reviewer
            var prompt = @$"Please determine if admin's message creates a task for reviewer'.

If the message contains a task for code reviewer, says: true, the task for code reviewer is xx
otherwise, says: false, the message doesn't contain a task for code reviewer

### admin's message ###
{lastMessage.Content}";

            var result = await helperAgent.SendAsync(prompt);

            return result.Content.ToLower().Contains("true");
        });

        var reviewerToAdminTransition = Transition.Create(codeReviewAgent, admin);

        var adminToUserTransition = Transition.Create(admin, userProxy, async (from, to, messages) =>
        {
            // the last message should be from admin
            var lastMessage = messages.Last();
            if (lastMessage.From != admin.Name)
            {
                return false;
            }

            // check if the last admin message create a task for user
            var prompt = @$"Please determine if admin's message contains a summary for user or has a question to user.

If the message contains a summary for user, says: true, the summary is xx
otherwise, says: false, the message doesn't contain a summary for user

### admin's message ###
{lastMessage.Content}";

            var result = await helperAgent.SendAsync(prompt);

            return result.Content.ToLower().Contains("true");
        });

        var userToAdminTransition = Transition.Create(userProxy, admin);

        var workflow = new Workflow(
            [
                adminToCoderTransition,
                coderToAdminTransition,
                adminToRunnerTransition,
                runnerToAdminTransition,
                adminToReviewerTransition,
                reviewerToAdminTransition,
                adminToUserTransition,
                userToAdminTransition,
            ]);
        // create group chat
        var groupChat = new GroupChat(
            admin: admin,
            members: [dotnetCoder, runner, codeReviewAgent, userProxy],
            workflow: workflow);

        var groupChatManager = new GroupChatManager(groupChat);
        await userProxy.SendAsync(groupChatManager, "Get the most recent PR from mlnet repo and save in pr.txt");

        File.Exists(prFile).Should().BeTrue();
    }
}
