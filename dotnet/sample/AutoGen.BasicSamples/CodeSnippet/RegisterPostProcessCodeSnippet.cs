// Copyright (c) Microsoft Corporation. All rights reserved.
// RegisterPostProcessCodeSnippet.cs

namespace AutoGen.BasicSample.CodeSnippet;

public class RegisterPostProcessCodeSnippet
{
    public async Task CodeSnippet1()
    {
        #region code_snippet_1
        IAgent agent = new DefaultReplyAgent("assistant", "Hello World");

        var agentWithPrettyPrintMessage = agent.RegisterPrintFormatMessageHook(); // print message to console

        // this is equivalent to
        agent = agent.RegisterPostProcess(async (conversation, reply, ct) =>
        {
            Console.WriteLine(reply.FormatMessage());

            return reply;
        });
        #endregion code_snippet_1
    }

    public async Task CodeSnippet2()
    {
        #region code_snippet_2
        IAgent agent = new DefaultReplyAgent("assistant", "Hello World");

        agent = agent
            .RegisterPostProcess(async (msgs, reply, ct) =>
            {
                Console.WriteLine("A");

                return reply;
            })
            .RegisterPostProcess(async (msgs, reply, ct) =>
            {
                Console.WriteLine("B");

                return reply;
            })
            .RegisterPostProcess(async (msgs, reply, ct) =>
            {
                Console.WriteLine("C");

                return reply;
            })
            .RegisterPrintFormatMessageHook(); // print message to console


        await agent.SendAsync("Hello World");

        // output:
        // A
        // B
        // C
        // Message from assistant
        // --------------------
        // content: Hello World
        // --------------------
        #endregion code_snippet_2
    }
}
