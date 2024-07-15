// Copyright (c) Microsoft Corporation. All rights reserved.
// Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs

using System.Text;
using System.Text.Json;
using AutoGen;
using AutoGen.BasicSample;
using AutoGen.Core;
using AutoGen.DotnetInteractive;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using FluentAssertions;

public partial class Example07_Dynamic_GroupChat_Calculate_Fibonacci
{
    #region reviewer_function
    public struct CodeReviewResult
    {
        public bool HasMultipleCodeBlocks { get; set; }
        public bool IsTopLevelStatement { get; set; }
        public bool IsDotnetCodeBlock { get; set; }
        public bool IsPrintResultToConsole { get; set; }
    }

    /// <summary>
    /// review code block
    /// </summary>
    /// <param name="hasMultipleCodeBlocks">true if there're multipe csharp code blocks</param>
    /// <param name="isTopLevelStatement">true if the code is in top level statement</param>
    /// <param name="isDotnetCodeBlock">true if the code block is csharp code block</param>
    /// <param name="isPrintResultToConsole">true if the code block print out result to console</param>
    [Function]
    public async Task<string> ReviewCodeBlock(
        bool hasMultipleCodeBlocks,
        bool isTopLevelStatement,
        bool isDotnetCodeBlock,
        bool isPrintResultToConsole)
    {
        var obj = new CodeReviewResult
        {
            HasMultipleCodeBlocks = hasMultipleCodeBlocks,
            IsTopLevelStatement = isTopLevelStatement,
            IsDotnetCodeBlock = isDotnetCodeBlock,
            IsPrintResultToConsole = isPrintResultToConsole,
        };

        return JsonSerializer.Serialize(obj);
    }
    #endregion reviewer_function

    #region create_coder
    public static async Task<IAgent> CreateCoderAgentAsync()
    {
        var gpt3Config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var coder = new GPTAgent(
            name: "coder",
            systemMessage: @"You act as dotnet coder, you write dotnet code to resolve task. Once you finish writing code, ask runner to run the code for you.

            Here're some rules to follow on writing dotnet code:
            - put code between ```csharp and ```
            - Avoid adding `using` keyword when creating disposable object. e.g `var httpClient = new HttpClient()`
            - Try to use `var` instead of explicit type.
            - Try avoid using external library, use .NET Core library instead.
            - Use top level statement to write code.
            - Always print out the result to console. Don't write code that doesn't print out anything.
            
            If you need to install nuget packages, put nuget packages in the following format:
            ```nuget
            nuget_package_name
            ```
            
            If your code is incorrect, runner will tell you the error message. Fix the error and send the code again.",
            config: gpt3Config,
            temperature: 0.4f)
            .RegisterPrintMessage();

        return coder;
    }
    #endregion create_coder

    #region create_runner
    public static async Task<IAgent> CreateRunnerAgentAsync(InteractiveService service)
    {
        var runner = new AssistantAgent(
            name: "runner",
            systemMessage: "You run dotnet code",
            defaultReply: "No code available.")
            .RegisterDotnetCodeBlockExectionHook(interactiveService: service)
            .RegisterMiddleware(async (msgs, option, agent, _) =>
            {
                if (msgs.Count() == 0 || msgs.All(msg => msg.From != "coder"))
                {
                    return new TextMessage(Role.Assistant, "No code available. Coder please write code");
                }
                else
                {
                    var coderMsg = msgs.Last(msg => msg.From == "coder");
                    return await agent.GenerateReplyAsync([coderMsg], option);
                }
            })
            .RegisterPrintMessage();

        return runner;
    }
    #endregion create_runner

    #region create_admin
    public static async Task<IAgent> CreateAdminAsync()
    {
        var gpt3Config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var admin = new GPTAgent(
            name: "admin",
            systemMessage: "You are group admin, terminate the group chat once task is completed by saying [TERMINATE] plus the final answer",
            temperature: 0,
            config: gpt3Config)
            .RegisterMiddleware(async (msgs, option, agent, _) =>
            {
                var reply = await agent.GenerateReplyAsync(msgs, option);
                if (reply is TextMessage textMessage && textMessage.Content.Contains("TERMINATE") is true)
                {
                    var content = $"{textMessage.Content}\n\n {GroupChatExtension.TERMINATE}";

                    return new TextMessage(Role.Assistant, content, from: reply.From);
                }

                return reply;
            });

        return admin;
    }
    #endregion create_admin

    #region create_reviewer
    public static async Task<IAgent> CreateReviewerAgentAsync()
    {
        var gpt3Config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var functions = new Example07_Dynamic_GroupChat_Calculate_Fibonacci();
        var reviewer = new GPTAgent(
            name: "code_reviewer",
            systemMessage: @"You review code block from coder",
            config: gpt3Config,
            functions: [functions.ReviewCodeBlockFunctionContract.ToOpenAIFunctionDefinition()],
            functionMap: new Dictionary<string, Func<string, Task<string>>>()
            {
                { nameof(ReviewCodeBlock), functions.ReviewCodeBlockWrapper },
            })
            .RegisterMiddleware(async (msgs, option, innerAgent, ct) =>
            {
                var maxRetry = 3;
                var reply = await innerAgent.GenerateReplyAsync(msgs, option, ct);
                while (maxRetry-- > 0)
                {
                    if (reply.GetToolCalls() is var toolCalls && toolCalls.Count() == 1 && toolCalls[0].FunctionName == nameof(ReviewCodeBlock))
                    {
                        var toolCallResult = reply.GetContent();
                        var reviewResultObj = JsonSerializer.Deserialize<CodeReviewResult>(toolCallResult);
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

                        if (reviewResultObj.IsPrintResultToConsole is false)
                        {
                            var fixCodeBlockPrompt = @"The code doesn't print out result to console, please print out result to console";
                            reviews.Add(fixCodeBlockPrompt);
                        }

                        if (reviews.Count > 0)
                        {
                            var sb = new StringBuilder();
                            sb.AppendLine("There're some comments from code reviewer, please fix these comments");
                            foreach (var review in reviews)
                            {
                                sb.AppendLine($"- {review}");
                            }

                            return new TextMessage(Role.Assistant, sb.ToString(), from: "code_reviewer");
                        }
                        else
                        {
                            var msg = new TextMessage(Role.Assistant, "The code looks good, please ask runner to run the code for you.")
                            {
                                From = "code_reviewer",
                            };

                            return msg;
                        }
                    }
                    else
                    {
                        var originalContent = reply.GetContent();
                        var prompt = $@"Please convert the content to ReviewCodeBlock function arguments.

        ## Original Content
        {originalContent}";

                        reply = await innerAgent.SendAsync(prompt, msgs, ct);
                    }
                }

                throw new Exception("Failed to review code block");
            })
            .RegisterPrintMessage();

        return reviewer;
    }
    #endregion create_reviewer

    public static async Task RunWorkflowAsync()
    {
        long the39thFibonacciNumber = 63245986;
        var workDir = Path.Combine(Path.GetTempPath(), "InteractiveService");
        if (!Directory.Exists(workDir))
        {
            Directory.CreateDirectory(workDir);
        }

        using var service = new InteractiveService(workDir);
        var dotnetInteractiveFunctions = new DotnetInteractiveFunction(service);

        await service.StartAsync(workDir, default);

        #region create_workflow
        var reviewer = await CreateReviewerAgentAsync();
        var coder = await CreateCoderAgentAsync();
        var runner = await CreateRunnerAgentAsync(service);
        var admin = await CreateAdminAsync();

        var admin2CoderTransition = Transition.Create(admin, coder);
        var coder2ReviewerTransition = Transition.Create(coder, reviewer);
        var reviewer2RunnerTransition = Transition.Create(
            from: reviewer,
            to: runner,
            canTransitionAsync: async (from, to, messages) =>
        {
            var lastMessage = messages.Last();
            if (lastMessage is TextMessage textMessage && textMessage.Content.ToLower().Contains("the code looks good, please ask runner to run the code for you.") is true)
            {
                // ask runner to run the code
                return true;
            }

            return false;
        });
        var reviewer2CoderTransition = Transition.Create(
            from: reviewer,
            to: coder,
            canTransitionAsync: async (from, to, messages) =>
        {
            var lastMessage = messages.Last();
            if (lastMessage is TextMessage textMessage && textMessage.Content.ToLower().Contains("there're some comments from code reviewer, please fix these comments") is true)
            {
                // ask coder to fix the code based on reviewer's comments
                return true;
            }

            return false;
        });

        var runner2CoderTransition = Transition.Create(
            from: runner,
            to: coder,
            canTransitionAsync: async (from, to, messages) =>
        {
            var lastMessage = messages.Last();
            if (lastMessage is TextMessage textMessage && textMessage.Content.ToLower().Contains("error") is true)
            {
                // ask coder to fix the error
                return true;
            }

            return false;
        });
        var runner2AdminTransition = Transition.Create(runner, admin);

        var workflow = new Graph(
            [
                admin2CoderTransition,
                coder2ReviewerTransition,
                reviewer2RunnerTransition,
                reviewer2CoderTransition,
                runner2CoderTransition,
                runner2AdminTransition,
            ]);
        #endregion create_workflow

        #region create_group_chat_with_workflow
        var groupChat = new GroupChat(
            admin: admin,
            workflow: workflow,
            members:
            [
                admin,
                coder,
                runner,
                reviewer,
            ]);

        admin.SendIntroduction("Welcome to my group, work together to resolve my task", groupChat);
        coder.SendIntroduction("I will write dotnet code to resolve task", groupChat);
        reviewer.SendIntroduction("I will review dotnet code", groupChat);
        runner.SendIntroduction("I will run dotnet code once the review is done", groupChat);

        var groupChatManager = new GroupChatManager(groupChat);
        var conversationHistory = await admin.InitiateChatAsync(groupChatManager, "What's the 39th of fibonacci number?", maxRound: 10);
        #endregion create_group_chat_with_workflow
        // the last message is from admin, which is the termination message
        var lastMessage = conversationHistory.Last();
        lastMessage.From.Should().Be("admin");
        lastMessage.IsGroupChatTerminateMessage().Should().BeTrue();
        lastMessage.Should().BeOfType<TextMessage>();
        lastMessage.GetContent().Should().Contain(the39thFibonacciNumber.ToString());
    }

    public static async Task RunAsync()
    {
        long the39thFibonacciNumber = 63245986;
        var workDir = Path.Combine(Path.GetTempPath(), "InteractiveService");
        if (!Directory.Exists(workDir))
        {
            Directory.CreateDirectory(workDir);
        }

        using var service = new InteractiveService(workDir);
        var dotnetInteractiveFunctions = new DotnetInteractiveFunction(service);

        await service.StartAsync(workDir, default);
        #region create_group_chat
        var reviewer = await CreateReviewerAgentAsync();
        var coder = await CreateCoderAgentAsync();
        var runner = await CreateRunnerAgentAsync(service);
        var admin = await CreateAdminAsync();
        var groupChat = new GroupChat(
            admin: admin,
            members:
            [
                admin,
                coder,
                runner,
                reviewer,
            ]);

        admin.SendIntroduction("Welcome to my group, work together to resolve my task", groupChat);
        coder.SendIntroduction("I will write dotnet code to resolve task", groupChat);
        reviewer.SendIntroduction("I will review dotnet code", groupChat);
        runner.SendIntroduction("I will run dotnet code once the review is done", groupChat);

        var groupChatManager = new GroupChatManager(groupChat);
        var conversationHistory = await admin.InitiateChatAsync(groupChatManager, "What's the 39th of fibonacci number?", maxRound: 10);

        // the last message is from admin, which is the termination message
        var lastMessage = conversationHistory.Last();
        lastMessage.From.Should().Be("admin");
        lastMessage.IsGroupChatTerminateMessage().Should().BeTrue();
        lastMessage.Should().BeOfType<TextMessage>();
        lastMessage.GetContent().Should().Contain(the39thFibonacciNumber.ToString());
        #endregion create_group_chat
    }
}
