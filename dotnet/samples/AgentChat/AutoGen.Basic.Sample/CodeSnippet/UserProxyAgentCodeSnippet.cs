// Copyright (c) Microsoft Corporation. All rights reserved.
// UserProxyAgentCodeSnippet.cs

using AutoGen.Core;

namespace AutoGen.Basic.Sample.CodeSnippet;

public class UserProxyAgentCodeSnippet
{
    public async Task CodeSnippet1()
    {
        #region code_snippet_1
        // create a user proxy agent which always ask user for input
        var agent = new UserProxyAgent(
            name: "user",
            humanInputMode: HumanInputMode.ALWAYS);

        await agent.SendAsync("hello");
        #endregion code_snippet_1
    }
}
