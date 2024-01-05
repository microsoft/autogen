// Copyright (c) Microsoft Corporation. All rights reserved.
// Example04_Dynamic_GroupChat_Get_MLNET_PR.cs

using System.Text.Json;
using AutoGen;
using AutoGen.DotnetInteractive.Extension;
using FluentAssertions;
using autogen = AutoGen.API;
using GroupChat = AutoGen.GroupChat;
using GroupChatExtension = AutoGen.GroupChatExtension;
using IAgent = AutoGen.IAgent;
using Message = AutoGen.Message;

public partial class Example04_Dynamic_GroupChat_Get_MLNET_PR
{
    /// <summary>
    /// create context for the current step
    /// </summary>
    /// <param name="previousCodeBlock">previous csharp code block.</param>
    /// <param name="step">current step.</param>
    /// <returns></returns>
    [FunctionAttribute]
    public async Task<string> CreateContextAndStep(string previousCodeBlock, string step)
    {
        return $@"// IGNORE THIS LINE [CONTEXT]
Please resolve the current step based on context

Here's the previous code block:
{previousCodeBlock}

Here's the current step:
{step}";
    }

    /// <summary>
    /// Get code block and output from conversation.
    /// </summary>
    /// <param name="codeBlock">code block</param>
    /// <param name="codeOutput">code output</param>
    [FunctionAttribute]
    public async Task<string> SummarizeCodeAndStep(string codeBlock, string codeOutput)
    {
        return $@"
// IGNORE THIS LINE [CODE_SOLUTION]
The existing code solution is:
{codeBlock}

The output of the code is:
{codeOutput}

{GroupChatExtension.TERMINATE}";
    }

    struct CodeReviewResult
    {
        public bool HasMultipleCodeBlocks { get; set; }
        public bool HasNugetPackages { get; set; }
        public bool IsTopLevelStatement { get; set; }
        public bool IsDotnetCodeBlock { get; set; }
        public bool IsUsingDeclartionHasBrace { get; set; }
    }

    /// <summary>
    /// review code block
    /// </summary>
    /// <param name="hasMultipleCodeBlocks">true if there're multipe csharp code blocks</param>
    /// <param name="hasNugetPackages">true if there's nuget package to install</param>
    /// <param name="isTopLevelStatement">true if the code is in top level statement</param>
    /// <param name="isUsingDeclartionHasBrace">true if the using declarition has brace. </param>
    /// <param name="isDotnetCodeBlock">true if the code block is csharp code block</param>
    [Function]
    public async Task<string> ReviewCodeBlock(
        bool hasMultipleCodeBlocks,
        bool hasNugetPackages,
        bool isTopLevelStatement,
        bool isUsingDeclartionHasBrace,
        bool isDotnetCodeBlock)
    {
        var obj = new CodeReviewResult
        {
            HasMultipleCodeBlocks = hasMultipleCodeBlocks,
            HasNugetPackages = hasNugetPackages,
            IsTopLevelStatement = isTopLevelStatement,
            IsDotnetCodeBlock = isDotnetCodeBlock,
            IsUsingDeclartionHasBrace = isUsingDeclartionHasBrace,
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
        var gpt3Config = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-3.5-turbo" });
        var gpt4Config = autogen.GetOpenAIConfigList(openAIKey, new[] { "gpt-4-1106-preview" });

        var steps = new[]
        {
            "Send a GET request to the GitHub API to retrieve the list of pull requests for the mlnet repo.",
            "Parse the response JSON to extract the latest pull request.",
            "Print the result to the console and save the result to a file named \"pr.txt\".",
        };

        // coding group
        // coding group will have three agents.
        // - admin : create step and summarize the conversation
        // - coder : write code
        // - runner : run code
        // coding group resolve one step at a time. Each time, admin will
        // provide context and current step to resolve.
        // coder will write code to resolve the current step.
        // runner will run the code from coder and install nuget packages.
        // if the code is correct, admin will summarize the context and current step.
        // if the code is wrong, coder will fix the code.

        // create admin agent
        var adminConfig = new ConversableAgentConfig
        {
            Temperature = 0,
            ConfigList = gpt3Config,
            FunctionDefinitions = new[]
            {
                instance.CreateContextAndStepFunction,
                instance.SummarizeCodeAndStepFunction,
            },
        };

        var admin = new AssistantAgent(
            name: "admin",
            systemMessage: @"You are admin, when conversation starts, you give the context and current step to resolve.
When coder write the code, you ask runner to run the code and collect the output.
When runner successfully run the code from coder, you summarize the code and step.
For other situation, you either ask coder to write code or ask runner to run code again.
",
            llmConfig: adminConfig,
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { nameof(CreateContextAndStep), instance.CreateContextAndStepWrapper },
                { nameof(SummarizeCodeAndStep), instance.SummarizeCodeAndStepWrapper },
            })
            .RegisterReply(async (msgs, _) =>
            {
                if (msgs.Last()?.From == "coder")
                {
                    return new Message(Role.Assistant, "runner, run code please");
                }

                return null;
            })
            .RegisterPrintFormatMessageHook();

        // create coder agent
        var coderConfig = new ConversableAgentConfig
        {
            Temperature = 0.4f,
            ConfigList = gpt3Config,
        };

        IAgent dotnetCoder = new AssistantAgent(
            name: "coder",
            systemMessage: @"You act as dotnet coder, you write dotnet code to resolve task. Once you finish writing code, ask runner to run the code for you.

Here're some rules to follow on writing dotnet code:
- put code between ```csharp and ```
- Add brace to using declaration when creating disposable object. e.g `using (var httpClient = new HttpClient())`
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
            llmConfig: coderConfig)
            .RegisterPrintFormatMessageHook();

        var codeReviewAgent = new AssistantAgent(
            name: "code_reviewer",
            systemMessage: @"You are a strict reviewer who reviews code block from coder's reply",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gpt3Config,
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

        var nugetAgent = new AssistantAgent(
           name: "nuget",
           systemMessage: @"Install nuget packages if there's any, otherwise say [NO_NUGET_PACKAGE]",
           llmConfig: new ConversableAgentConfig
           {
               Temperature = 0,
               ConfigList = gpt3Config,
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

        var coder = dotnetCoder.RegisterPostProcess(async (conversation, reply, ct) =>
        {
            // review code block
            while (true)
            {
                var reviewResult = await codeReviewAgent.SendAsync(reply);
                var reviewResultObj = JsonSerializer.Deserialize<CodeReviewResult>(reviewResult.Content!);
                if (reviewResultObj.HasMultipleCodeBlocks)
                {
                    var fixCodeBlockPrompt = @"There're multiple code blocks, please combine them into one code block";
                    var fixCodeBlockMessage = new Message(Role.System, fixCodeBlockPrompt);
                    var chatHistory = new[]
                    {
                        fixCodeBlockMessage,
                        reply,
                    };
                    reply = await dotnetCoder.SendAsync(chatHistory: chatHistory);
                    continue;
                }

                if (reviewResultObj.IsUsingDeclartionHasBrace is false)
                {
                    var fixCodeBlockPrompt = @"The using declation before disposable object doesn't have brace. Please either adding brace or remove the using declarition";
                    var fixCodeBlockMessage = new Message(Role.System, fixCodeBlockPrompt);
                    var chatHistory = new[]
                    {
                        fixCodeBlockMessage,
                        reply,
                    };
                    reply = await dotnetCoder.SendAsync(chatHistory: chatHistory);
                    continue;
                }

                if (reviewResultObj.IsDotnetCodeBlock is false)
                {
                    var fixCodeBlockPrompt = @"The code block is not csharp code block, please write dotnet code only";
                    var fixCodeBlockMessage = new Message(Role.System, fixCodeBlockPrompt);
                    var chatHistory = new[]
                    {
                        fixCodeBlockMessage,
                        reply,
                    };
                    reply = await dotnetCoder.SendAsync(chatHistory: chatHistory);
                    continue;
                }

                if (reviewResultObj.IsTopLevelStatement is false)
                {
                    var fixCodeBlockPrompt = @"The code is not top level statement, please rewrite your dotnet code using top level statement";
                    var fixCodeBlockMessage = new Message(Role.System, fixCodeBlockPrompt);
                    var chatHistory = new[]
                    {
                        fixCodeBlockMessage,
                        reply,
                    };
                    reply = await dotnetCoder.SendAsync(chatHistory: chatHistory);
                    continue;
                }

                if (reviewResultObj.HasNugetPackages)
                {
                    var installNugetPrompt = @"There're nuget packages to install, please install them";
                    var installNugetMessage = new Message(Role.System, installNugetPrompt);
                    var chatHistory = new[]
                    {
                        installNugetMessage,
                        reply,
                    };
                    await nugetAgent.SendAsync(chatHistory: chatHistory);
                }

                return reply;
            }
        });

        var runner = new AssistantAgent(
            name: "runner",
            defaultReply: "No code available, coder, write code please",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gpt3Config,
            })
            .RegisterDotnetCodeBlockExectionHook(interactiveService: service)
            .RegisterReply(async (msgs, ct) =>
            {
                // retrieve code from the last message
                // if the last message is not from coder, ask coder to write code
                var lastMessage = msgs.Last();
                if (lastMessage.From != "coder")
                {
                    return new Message(Role.Assistant, "coder, write code please");
                }

                return null;
            })
            .RegisterPrintFormatMessageHook();

        // create group chat
        var groupChat = new GroupChat(
            admin: admin,
            agents: new IAgent[] { coder, runner });

        admin.AddInitializeMessage("Welcome to the group chat! Work together to resolve my task.", groupChat);
        coder.AddInitializeMessage("Hey I'm Coder, I write dotnet code.", groupChat);
        runner.AddInitializeMessage("Hey I'm Runner, I run dotnet code from coder.", groupChat);

        // start group chat
        var groupChatManager = new GroupChatManager(groupChat);
        var previousContext = string.Empty;
        foreach (var step in steps)
        {
            var createContextForCurrentStepPrompt = @$"Create context for current step
previous context: {previousContext}

Step: {step}";

            var history = new[]
            {
                new Message(Role.System, createContextForCurrentStepPrompt),
            };
            var reply = await admin.SendAsync(createContextForCurrentStepPrompt);
            IEnumerable<Message> chatHistoryForCurrentStep = new[]
            {
                reply,
            };
            chatHistoryForCurrentStep = await admin.SendAsync(groupChatManager, chatHistoryForCurrentStep, maxRound: 20);
            var previousContextMessage = chatHistoryForCurrentStep.Last(m => m.Content?.Contains("[CODE_SOLUTION]") ?? false);
            previousContext = previousContextMessage.Content;
        }

        File.Exists(prFile).Should().BeTrue();
    }
}
