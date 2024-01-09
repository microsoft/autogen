// Copyright (c) Microsoft Corporation. All rights reserved.
// RegisterPreprocessCodeSnippet.cs

namespace AutoGen.BasicSample.CodeSnippet;

public class RegisterPreprocessCodeSnippet
{
    public async Task CodeSnippet1()
    {
        IAgent codeReviewer = default;

        #region code_snippet_1
        codeReviewer = codeReviewer
            .RegisterPreProcess(async (msgs, ct) =>
            {
                // only keep the last message from coder for codeReviewer to review
                var coderMessage = msgs.Last(m => m.From == "coder");

                return new[]
                {
                    coderMessage,
                };
            });
        #endregion code_snippet_1
    }

    public async Task CodeSnippet2()
    {
        #region code_snippet_2
        IAgent agent = new DefaultReplyAgent("assistant", "Hello World")
            .RegisterPrintFormatMessageHook(); // print message to console

        agent = agent
            .RegisterPreProcess(async (msgs, ct) =>
            {
                Console.WriteLine("A");

                return msgs;
            })
            .RegisterPreProcess(async (msgs, ct) =>
            {
                Console.WriteLine("B");

                return msgs;
            })
            .RegisterPreProcess(async (msgs, ct) =>
            {
                Console.WriteLine("C");

                return msgs;
            });

        await agent.SendAsync("Hello World");

        // output:
        // C
        // B
        // A
        // Message from assistant
        // --------------------
        // content: Hello World
        // --------------------
        #endregion code_snippet_2
    }
}
