# 🎉 Release Notes: AutoGen.Net 0.1.0 🎉

## 📦 New Packages

1. **Add AutoGen.AzureAIInference Package**
   - **Issue**: [.Net][Feature Request] [#3323](https://github.com/microsoft/autogen/issues/3323)
   - **Description**: The new `AutoGen.AzureAIInference` package includes the `ChatCompletionClientAgent`.

## ✨ New Features

1. **Enable Step-by-Step Execution for Two Agent Chat API**
   - **Issue**: [.Net][Feature Request] [#3339](https://github.com/microsoft/autogen/issues/3339)
   - **Description**: The `AgentExtension.SendAsync` now returns an `IAsyncEnumerable`, allowing conversations to be driven step by step, similar to how `GroupChatExtension.SendAsync` works.

2. **Support Python Code Execution in AutoGen.DotnetInteractive**
   - **Issue**: [.Net][Feature Request] [#3316](https://github.com/microsoft/autogen/issues/3316)
   - **Description**: `dotnet-interactive` now supports Jupyter kernel connection, allowing Python code execution in `AutoGen.DotnetInteractive`.

3. **Support Prompt Cache in Claude**
   - **Issue**: [.Net][Feature Request] [#3359](https://github.com/microsoft/autogen/issues/3359)
   - **Description**: Claude now supports prompt caching, which dramatically lowers the bill if the cache is hit. Added the corresponding option in the Claude client.

## 🐛 Bug Fixes

1. **GroupChatExtension.SendAsync Doesn’t Terminate Chat When `IOrchestrator` Returns Null as Next Agent**
   - **Issue**: [.Net][Bug] [#3306](https://github.com/microsoft/autogen/issues/3306)
   - **Description**: Fixed an issue where `GroupChatExtension.SendAsync` would continue until the max_round is reached even when `IOrchestrator` returns null as the next speaker.

2. **InitializedMessages Are Added Repeatedly in GroupChatExtension.SendAsync Method**
   - **Issue**: [.Net][Bug] [#3268](https://github.com/microsoft/autogen/issues/3268)
   - **Description**: Fixed an issue where initialized messages from group chat were being added repeatedly in every iteration of the `GroupChatExtension.SendAsync` API.

3. **Remove `Azure.AI.OpenAI` Dependency from `AutoGen.DotnetInteractive`**
   - **Issue**: [.Net][Feature Request] [#3273](https://github.com/microsoft/autogen/issues/3273)
   - **Description**: Fixed an issue by removing the `Azure.AI.OpenAI` dependency from `AutoGen.DotnetInteractive`, simplifying the package and reducing dependencies.

## 📄 Documentation Updates

1. **Add Function Comparison Page Between Python AutoGen and AutoGen.Net**
   - **Issue**: [.Net][Document] [#3184](https://github.com/microsoft/autogen/issues/3184)
   - **Description**: Added comparative documentation for features between AutoGen and AutoGen.Net across various functionalities and platform supports.