// Copyright (c) Microsoft Corporation. All rights reserved.
// Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs

using System.Text.Json;
using AutoGen.DotnetInteractive;
using AutoGen;
using System.Text;
using FluentAssertions;
using AutoGen.Core.API;

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


    public static async Task RunAsync()
    {
        var functions = new Example07_Dynamic_GroupChat_Calculate_Fibonacci();
        long the39thFibonacciNumber = 63245986;
        var workDir = Path.Combine(Path.GetTempPath(), "InteractiveService");
        if (!Directory.Exists(workDir))
            Directory.CreateDirectory(workDir);

        var service = new InteractiveService(workDir);
        var dotnetInteractiveFunctions = new DotnetInteractiveFunction(service);

        await service.StartAsync(workDir, default);

        // get OpenAI Key and create config
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var gpt3Config = LLMConfigAPI.GetOpenAIConfigList(openAIKey, new[] { "gpt-3.5-turbo" });

        #region create_reviewer
        var reviewer = new AssistantAgent(
            name: "code_reviewer",
            systemMessage: @"You review code block from coder",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gpt3Config,
                FunctionDefinitions = new[]
                {
                    functions.ReviewCodeBlockFunction,
                },
            },
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
                    if (reply.FunctionName == nameof(ReviewCodeBlock))
                    {
                        var reviewResultObj = JsonSerializer.Deserialize<CodeReviewResult>(reply.Content!);
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

                            reply.Content = sb.ToString();

                            return reply;
                        }
                        else
                        {
                            var msg = new Message(Role.Assistant, "The code looks good, please ask runner to run the code for you.")
                            {
                                From = "code_reviewer",
                            };

                            return msg;
                        }
                    }
                    else
                    {
                        var originalContent = reply.Content;
                        var prompt = $@"Please convert the content to ReviewCodeBlock function arguments.

## Original Content
{originalContent}";

                        reply = await innerAgent.SendAsync(prompt, msgs, ct);
                    }
                }

                throw new Exception("Failed to review code block");
            })
            .RegisterPrintFormatMessageHook();
        #endregion create_reviewer

        #region create_coder
        var coder = new AssistantAgent(
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
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0.4f,
                ConfigList = gpt3Config,
            })
            .RegisterPrintFormatMessageHook();
        #endregion create_coder

        #region create_runner
        var runner = new AssistantAgent(
            name: "runner",
            systemMessage: "You run dotnet code",
            defaultReply: "No code available.")
            .RegisterDotnetCodeBlockExectionHook(interactiveService: service)
            .RegisterReply(async (msgs, _) =>
            {
                if (msgs.Count() == 0)
                {
                    return new Message(Role.Assistant, "No code available. Coder please write code");
                }

                return null;
            })
            .RegisterPreProcess(async (msgs, _) =>
            {
                // retrieve the most recent message from coder
                var coderMsg = msgs.LastOrDefault(msg => msg.From == "coder");
                if (coderMsg is null)
                {
                    return Enumerable.Empty<Message>();
                }
                else
                {
                    return new[] { coderMsg };
                }
            })
            .RegisterPrintFormatMessageHook();
        #endregion create_runner

        #region create_admin
        var admin = new AssistantAgent(
            name: "admin",
            systemMessage: "You are group admin, terminate the group chat once task is completed by saying [TERMINATE] plus the final answer",
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = gpt3Config,
            })
            .RegisterPostProcess(async (_, reply, _) =>
            {
                if (reply.Content?.Contains("TERMINATE") is true)
                {
                    reply.Content += $"\n\n {GroupChatExtension.TERMINATE}";
                }

                return reply;
            })
            .RegisterPrintFormatMessageHook();
        #endregion create_admin

        #region create_group_chat
        var groupChat = new GroupChat(
            admin: admin,
            members:
            [
                admin,
                coder,
                runner,
                reviewer,
            ]);

        admin.AddInitializeMessage("Welcome to my group, work together to resolve my task", groupChat);
        coder.AddInitializeMessage("I will write dotnet code to resolve task", groupChat);
        reviewer.AddInitializeMessage("I will review dotnet code", groupChat);
        runner.AddInitializeMessage("I will run dotnet code once the review is done", groupChat);

        var groupChatManager = new GroupChatManager(groupChat);
        #endregion create_group_chat

        #region start_group_chat
        var conversationHistory = await admin.InitiateChatAsync(groupChatManager, "What's the 39th of fibonacci number?", maxRound: 10);

        // the last message is from admin, which is the termination message
        var lastMessage = conversationHistory.Last();
        lastMessage.From.Should().Be("admin");
        lastMessage.IsGroupChatTerminateMessage().Should().BeTrue();
        lastMessage.Content.Should().Contain(the39thFibonacciNumber.ToString());
        #endregion start_group_chat
    }
}
