// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// UserProxyAgentCodeSnippet.cs
using AutoGen.Core;

namespace AutoGen.BasicSample.CodeSnippet;

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
