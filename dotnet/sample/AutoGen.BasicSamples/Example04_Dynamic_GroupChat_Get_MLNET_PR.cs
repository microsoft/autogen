// Copyright (c) Microsoft Corporation. All rights reserved.
// Example04_Dynamic_GroupChat_Get_MLNET_PR.cs

using AutoGen;
using AutoGen.Extension;
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
    /// <param name="previousCodeContext">previous csharp code context.</param>
    /// <param name="step">current step.</param>
    /// <returns></returns>
    [FunctionAttribution]
    public async Task<string> CreateContextAndStep(string previousCodeContext, string step)
    {
        return $@"// IGNORE THIS LINE [CONTEXT]
Here's the previous code context:
{previousCodeContext}

Here's the current step:
{step}

Please resolve the current step based on context";
    }

    /// <summary>
    /// summarize the current step and code solution and output.
    /// </summary>
    /// <param name="code">code solution</param>
    /// <param name="step">step</param>
    /// <param name="output">code output</param>
    [FunctionAttribution]
    public async Task<string> SummarizeCodeAndStep(string code, string step, string output)
    {
        return $@"
// IGNORE THIS LINE [CODE_SOLUTION]
The existing code solution is:
{code}

The output of the code is:
{output}

{GroupChatExtension.TERMINATE}";
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
When runner successfully run the code from coder, you summarize the code and step.
For other situation, you either ask coder to write code or ask runner to run code again.
",
            llmConfig: adminConfig,
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { nameof(CreateContextAndStep), instance.CreateContextAndStepWrapper },
                { nameof(SummarizeCodeAndStep), instance.SummarizeCodeAndStepWrapper },
            }).PrintFormatMessage();

        // create coder agent
        var coderConfig = new ConversableAgentConfig
        {
            Temperature = 0,
            ConfigList = gpt3Config,
        };

        IAgent coder = new AssistantAgent(
            name: "coder",
            systemMessage: @"You act as dotnet coder, you write dotnet script to resolve task. Once you finish writing code, ask runner to run the code for you.

Here're some rules to follow on writing dotnet code:
- put code between ```csharp and ```
- Use top-level statements, remove main function, just write code, like what python does.
- Remove all `using` statement. Runner can't handle it.
- Try to use `var` instead of explicit type.
- Try avoid using external library.
- Don't use external data source, like file, database, etc. Create a dummy dataset if you need.
- Always print out the result to console. Don't write code that doesn't print out anything.

If you need to install nuget packages, put nuget packages in the following format:
```nuget
nuget_package_name
```

If your code is incorrect, runner will tell you the error message. Fix the error and send the code again.

Here's some externel information
- The link to mlnet repo is: https://github.com/dotnet/machinelearning. you don't need a token to use github pr api. Make sure to include a User-Agent header, otherwise github will reject it.
",
            llmConfig: coderConfig).PrintFormatMessage();

        // create runner agent
        var runnerConfig = new ConversableAgentConfig
        {
            Temperature = 0,
            ConfigList = gpt4Config,
            FunctionDefinitions = new[]
            {
                dotnetInteractiveFunctions.InstallNugetPackagesFunction,
                dotnetInteractiveFunctions.RunCodeFunction,
            },
        };

        IAgent dotnetRunner = new AssistantAgent(
            name: "runner",
            systemMessage: @"You are dotnet code runner, you run dotnet code from coder.
If the message contains nuget package block. Install nuget package first.
Otherwise, run the code from coder.",
            llmConfig: runnerConfig,
            defaultReply: "NO_CODE_AVAILABLE",
            functionMap: new Dictionary<string, Func<string, Task<string>>>()
            {
                { dotnetInteractiveFunctions.InstallNugetPackagesFunction.Name, dotnetInteractiveFunctions.InstallNugetPackagesWrapper },
                { dotnetInteractiveFunctions.RunCodeFunction.Name, dotnetInteractiveFunctions.RunCodeWrapper },
            });

        var critic = new AssistantAgent(
            name: "runner",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gpt3Config,
            });

        var runner = critic.
            RegisterReply(async (msgs, ct) =>
            {
                // retrieve code from the last message
                // if the last message is not from coder, ask coder to write code
                var lastMessage = msgs.Last();
                if (lastMessage.From != "coder")
                {
                    return new Message(Role.Assistant, "coder, write code please");
                }

                // if last message contains nuget package, install nuget package
                var prompt = @$"Your task is to check if there's any nuget block in given message. The nuget block is in the following format:
```nuget
// nuget package name
```

if there's no nuget block, say [NO_NUGET_BLOCK]
Otherwise, return the content of nuget block.

### message ###
{lastMessage.Content}
### end ###";
                var chatHistory = new[]
                {
                    new Message(Role.User, prompt),
                };

                var reply = await critic.SendAsync(chatHistory: chatHistory);
                if (reply.Content?.Contains("NO_NUGET_BLOCK") is false)
                {
                    Console.WriteLine($"install nuget package: {reply.Content}");
                    var installNugetHistory = new[]
                    {
                        new Message(Role.System, "install nuget package"),
                        reply,
                    };
                    await dotnetRunner.SendAsync(chatHistory: installNugetHistory);
                }

                prompt = $@"You are a helpful AI assistant.
Your task is to retrieve csharp code from user message.

If there's no code block, say [NO_CODE_BLOCK]

If there're multiple code blocks, merge them into one code block. Carefully consider the order of the code blocks before merging them.
Put the merged code block between ```csharp and ```

user message:
{lastMessage.Content}";
                chatHistory = new[]
                {
                    new Message(Role.System, prompt),
                };

                reply = await critic.SendAsync(chatHistory: chatHistory);
                if (reply.Content?.Contains("NO_CODE_BLOCK") is true)
                {
                    return new Message(Role.Assistant, "coder, write code please");
                }

                // check if the code is in top level statement
                if (reply.Content?.Contains("Main") is true)
                {
                    return new Message(Role.Assistant, "coder, write code using top level statement, remove main function");
                }

                // Good to go
                // run the code
                prompt = $@"Run code below

{reply.Content}";
                chatHistory = new[]
                {
                    new Message(Role.User, prompt),
                };

                return await dotnetRunner.SendAsync(chatHistory: chatHistory);
            }).PrintFormatMessage();

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
        var currentStep = string.Empty;

        foreach (var step in steps)
        {
            currentStep = step;

            var createContextForCurrentStepPrompt = @$"Create context for current step
previous context: {previousContext}

Step: {currentStep}";

            var history = new[]
            {
                new Message(Role.System, createContextForCurrentStepPrompt),
            };
            var reply = await admin.SendAsync(createContextForCurrentStepPrompt);
            IEnumerable<Message> chatHistoryForCurrentStep = new[]
            {
                reply,
            };
            var maxRound = 20;
            chatHistoryForCurrentStep = await admin.SendAsync(groupChatManager, chatHistoryForCurrentStep, maxRound: maxRound);

            var previousContextMessage = chatHistoryForCurrentStep.Last(m => m.Content?.Contains("[CODE_SOLUTION]") ?? false);
            previousContext = previousContextMessage.Content;
        }

        File.Exists(prFile).Should().BeTrue();
    }
}
