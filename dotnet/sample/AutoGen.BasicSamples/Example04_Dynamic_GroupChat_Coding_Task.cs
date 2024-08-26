// Copyright (c) Microsoft Corporation. All rights reserved.
// Example04_Dynamic_GroupChat_Coding_Task.cs

using AutoGen;
using AutoGen.BasicSample;
using AutoGen.Core;
using AutoGen.DotnetInteractive;
using AutoGen.DotnetInteractive.Extension;
using AutoGen.OpenAI.V1;
using FluentAssertions;

public partial class Example04_Dynamic_GroupChat_Coding_Task
{
    public static async Task RunAsync()
    {
        var instance = new Example04_Dynamic_GroupChat_Coding_Task();

        var kernel = DotnetInteractiveKernelBuilder
            .CreateDefaultInProcessKernelBuilder()
            .AddPythonKernel("python3")
            .Build();

        var gptConfig = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();

        var groupAdmin = new GPTAgent(
            name: "groupAdmin",
            systemMessage: "You are the admin of the group chat",
            temperature: 0f,
            config: gptConfig)
            .RegisterPrintMessage();

        var userProxy = new UserProxyAgent(name: "user", defaultReply: GroupChatExtension.TERMINATE, humanInputMode: HumanInputMode.NEVER)
            .RegisterPrintMessage();

        // Create admin agent
        var admin = new AssistantAgent(
            name: "admin",
            systemMessage: """
            You are a manager who takes coding problem from user and resolve problem by splitting them into small tasks and assign each task to the most appropriate agent.
            Here's available agents who you can assign task to:
            - coder: write python code to resolve task
            - runner: run python code from coder

            The workflow is as follows:
            - You take the coding problem from user
            - You break the problem into small tasks. For each tasks you first ask coder to write code to resolve the task. Once the code is written, you ask runner to run the code.
            - Once a small task is resolved, you summarize the completed steps and create the next step.
            - You repeat the above steps until the coding problem is resolved.

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

            Once the coding problem is resolved, summarize each steps and results and send the summary to the user using the following format:
            ```summary
            @user, <summary of the task>
            ```

            Your reply must contain one of [task|ask|summary] to indicate the type of your message.
            """,
            llmConfig: new ConversableAgentConfig
            {
                Temperature = 0,
                ConfigList = [gptConfig],
            })
            .RegisterPrintMessage();

        // create coder agent
        // The coder agent is a composite agent that contains dotnet coder, code reviewer and nuget agent.
        // The dotnet coder write dotnet code to resolve the task.
        // The code reviewer review the code block from coder's reply.
        // The nuget agent install nuget packages if there's any.
        var coderAgent = new GPTAgent(
            name: "coder",
            systemMessage: @"You act as python coder, you write python code to resolve task. Once you finish writing code, ask runner to run the code for you.

Here're some rules to follow on writing dotnet code:
- put code between ```python and ```
- Try avoid using external library
- Always print out the result to console. Don't write code that doesn't print out anything.

Use the following format to install pip package:
```python
%pip install <package_name>
```

If your code is incorrect, Fix the error and send the code again.

Here's some externel information
- The link to mlnet repo is: https://github.com/dotnet/machinelearning. you don't need a token to use github pr api. Make sure to include a User-Agent header, otherwise github will reject it.
",
            config: gptConfig,
            temperature: 0.4f)
            .RegisterPrintMessage();

        // code reviewer agent will review if code block from coder's reply satisfy the following conditions:
        // - There's only one code block
        // - The code block is csharp code block
        // - The code block is top level statement
        // - The code block is not using declaration
        var codeReviewAgent = new GPTAgent(
            name: "reviewer",
            systemMessage: """
            You are a code reviewer who reviews code from coder. You need to check if the code satisfy the following conditions:
            - The reply from coder contains at least one code block, e.g ```python and ```
            - There's only one code block and it's python code block

            You don't check the code style, only check if the code satisfy the above conditions.

            Put your comment between ```review and ```, if the code satisfies all conditions, put APPROVED in review.result field. Otherwise, put REJECTED along with comments. make sure your comment is clear and easy to understand.
            
            ## Example 1 ##
            ```review
            comment: The code satisfies all conditions.
            result: APPROVED
            ```

            ## Example 2 ##
            ```review
            comment: The code is inside main function. Please rewrite the code in top level statement.
            result: REJECTED
            ```

            """,
            config: gptConfig,
            temperature: 0f)
            .RegisterPrintMessage();

        // create runner agent
        // The runner agent will run the code block from coder's reply.
        // It runs dotnet code using dotnet interactive service hook.
        // It also truncate the output if the output is too long.
        var runner = new DefaultReplyAgent(
            name: "runner",
            defaultReply: "No code available, coder, write code please")
            .RegisterMiddleware(async (msgs, option, agent, ct) =>
            {
                var mostRecentCoderMessage = msgs.LastOrDefault(x => x.From == "coder") ?? throw new Exception("No coder message found");

                if (mostRecentCoderMessage.ExtractCodeBlock("```python", "```") is string code)
                {
                    var result = await kernel.RunSubmitCodeCommandAsync(code, "python");
                    // only keep the first 500 characters
                    if (result.Length > 500)
                    {
                        result = result.Substring(0, 500);
                    }
                    result = $"""
                    # [CODE_BLOCK_EXECUTION_RESULT]
                    {result}
                    """;

                    return new TextMessage(Role.Assistant, result, from: agent.Name);
                }
                else
                {
                    return await agent.GenerateReplyAsync(msgs, option, ct);
                }
            })
            .RegisterPrintMessage();

        var adminToCoderTransition = Transition.Create(admin, coderAgent, async (from, to, messages) =>
        {
            // the last message should be from admin
            var lastMessage = messages.Last();
            if (lastMessage.From != admin.Name)
            {
                return false;
            }

            return true;
        });
        var coderToReviewerTransition = Transition.Create(coderAgent, codeReviewAgent);
        var adminToRunnerTransition = Transition.Create(admin, runner, async (from, to, messages) =>
        {
            // the last message should be from admin
            var lastMessage = messages.Last();
            if (lastMessage.From != admin.Name)
            {
                return false;
            }

            // the previous messages should contain a message from coder
            var coderMessage = messages.FirstOrDefault(x => x.From == coderAgent.Name);
            if (coderMessage is null)
            {
                return false;
            }

            return true;
        });

        var runnerToAdminTransition = Transition.Create(runner, admin);

        var reviewerToAdminTransition = Transition.Create(codeReviewAgent, admin);

        var adminToUserTransition = Transition.Create(admin, userProxy, async (from, to, messages) =>
        {
            // the last message should be from admin
            var lastMessage = messages.Last();
            if (lastMessage.From != admin.Name)
            {
                return false;
            }

            return true;
        });

        var userToAdminTransition = Transition.Create(userProxy, admin);

        var workflow = new Graph(
            [
                adminToCoderTransition,
                coderToReviewerTransition,
                reviewerToAdminTransition,
                adminToRunnerTransition,
                runnerToAdminTransition,
                adminToUserTransition,
                userToAdminTransition,
            ]);

        // create group chat
        var groupChat = new GroupChat(
            admin: groupAdmin,
            members: [admin, coderAgent, runner, codeReviewAgent, userProxy],
            workflow: workflow);

        // task 1: retrieve the most recent pr from mlnet and save it in result.txt
        var task = """
            retrieve the most recent pr from mlnet and save it in result.txt
            """;
        var chatHistory = new List<IMessage>
        {
            new TextMessage(Role.Assistant, task)
            {
                From = userProxy.Name
            }
        };
        await foreach (var message in groupChat.SendAsync(chatHistory, maxRound: 10))
        {
            if (message.From == admin.Name && message.GetContent().Contains("```summary"))
            {
                // Task complete!
                break;
            }
        }

        // check if the result file is created
        var result = "result.txt";
        File.Exists(result).Should().BeTrue();
    }
}
