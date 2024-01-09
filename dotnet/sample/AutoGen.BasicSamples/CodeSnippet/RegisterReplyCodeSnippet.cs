// Copyright (c) Microsoft Corporation. All rights reserved.
// RegisterReplyCodeSnippet.cs

namespace AutoGen.BasicSample.CodeSnippet;

public class RegisterReplyCodeSnippet
{
    public async Task CodeSnippet1()
    {
        #region code_snippet_1
        IAgent agent = new DefaultReplyAgent("assistant", "Hello World")
            .RegisterPrintFormatMessageHook(); // print message to console

        agent = agent
            .RegisterReply(async (msgs, ct) =>
            {
                Console.WriteLine("A");

                // return null so that the inner agent can continue to process the message
                return null;
            })
            .RegisterReply(async (msgs, ct) =>
            {
                Console.WriteLine("B");

                // return null so that the inner agent can continue to process the message
                return null;
            })
            .RegisterReply(async (msgs, ct) =>
            {
                Console.WriteLine("C");

                // return null so that the inner agent can continue to process the message
                return null;
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
        #endregion code_snippet_1
    }
}
