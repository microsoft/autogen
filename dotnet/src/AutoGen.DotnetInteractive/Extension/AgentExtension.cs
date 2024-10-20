// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExtension.cs

using System.Text;
namespace AutoGen.DotnetInteractive;

public static class AgentExtension
{
    /// <summary>
    /// Register an AutoReply hook to run dotnet code block from message.
    /// This hook will first detect if there's any dotnet code block (e.g. ```csharp and ```) in the most recent message.
    /// if there's any, it will run the code block and send the result back as reply.
    /// </summary>
    /// <param name="agent">agent</param>
    /// <param name="interactiveService">interactive service</param>
    /// <param name="codeBlockPrefix">code block prefix</param>
    /// <param name="codeBlockSuffix">code block suffix</param>
    /// <param name="maximumOutputToKeep">maximum output to keep</param>
    /// <example>
    /// <![CDATA[
    /// [!code-csharp[Example04_Dynamic_GroupChat_Coding_Task](~/../sample/AutoGen.BasicSamples/Example04_Dynamic_GroupChat_Coding_Task.cs)]
    /// ]]>
    /// </example>
    [Obsolete]
    public static IAgent RegisterDotnetCodeBlockExectionHook(
        this IAgent agent,
        InteractiveService interactiveService,
        string codeBlockPrefix = "```csharp",
        string codeBlockSuffix = "```",
        int maximumOutputToKeep = 500)
    {
        return agent.RegisterMiddleware(async (msgs, option, innerAgent, ct) =>
        {
            var lastMessage = msgs.LastOrDefault();
            if (lastMessage == null || lastMessage.GetContent() is null)
            {
                return await innerAgent.GenerateReplyAsync(msgs, option, ct);
            }

            // retrieve all code blocks from last message
            var codeBlocks = lastMessage.GetContent()!.Split(new[] { codeBlockPrefix }, StringSplitOptions.RemoveEmptyEntries);
            if (codeBlocks.Length <= 0)
            {
                return await innerAgent.GenerateReplyAsync(msgs, option, ct);
            }

            // run code blocks
            var result = new StringBuilder();
            var i = 0;
            result.AppendLine(@$"// [DOTNET_CODE_BLOCK_EXECUTION]");
            foreach (var codeBlock in codeBlocks)
            {
                var codeBlockIndex = codeBlock.IndexOf(codeBlockSuffix);

                if (codeBlockIndex == -1)
                {
                    continue;
                }

                // remove code block suffix
                var code = codeBlock.Substring(0, codeBlockIndex).Trim();

                if (code.Length == 0)
                {
                    continue;
                }

                var codeResult = await interactiveService.SubmitCSharpCodeAsync(code, ct);
                if (codeResult != null)
                {
                    result.AppendLine(@$"### Executing result for code block {i++}");
                    result.AppendLine(codeResult);
                    result.AppendLine("### End of executing result ###");
                }
            }
            if (result.Length <= maximumOutputToKeep)
            {
                maximumOutputToKeep = result.Length;
            }

            return new TextMessage(Role.Assistant, result.ToString().Substring(0, maximumOutputToKeep), from: agent.Name);
        });
    }
}
