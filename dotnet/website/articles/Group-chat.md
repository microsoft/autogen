@AutoGen.GroupChat provides native support for a dynamic group chat communication pattern, in which participating agents share the same context and converse with the others in a dynamic manner. Dynamic group chat relies on ongoing conversations to guide the flow of interaction among agents. These make dynamic group chat ideal for situations where collaboration without strict communication order is beneficial

> [!TIP]
> @AutoGen.GroupChat replies on `admin` agent to orchestrate the conversation flow. To achieve more comprehensive result, it's recommended to use a more powerful LLM model for `admin` agent, like `GPT-4` series.

## Case study: Create a dynamic group chat

The following example shows how to create a dynamic group chat with @AutoGen.GroupChat. In this example, we will create a dynamic group chat with 4 agents: `admin`, `coder`, `reviewer` and `runner`. Each agent has its own role in the group chat:
- `admin`: create task for group to work on and terminate the conversation when task is completed. In this example, the task to resolve is to calculate the 39th Fibonacci number.
- `coder`: a dotnet coder who can write code to resolve tasks.
- `reviewer`: a dotnet code reviewer who can review code written by `coder`. In this example, `reviewer` will examine if the code written by `coder` follows the condition below:
  - has only one csharp code block.
  - use top-level statements.
  - is dotnet code snippet.
  - print the result of the code snippet to console.
- `runner`: a dotnet code runner who can run code written by `coder` and print the result.

> [!NOTE]
> The complete code of this example can be found in `Example07_Dynamic_GroupChat_Calculate_Fibonacci`

### Create admin agent

The code below shows how to create `admin` agent. `admin` agent will create a task for group to work on and terminate the conversation when task is completed.

[!code-csharp[](../../sample/AutoGen.BasicSamples/Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs?name=create_admin)]

> [!TIP]
> You can use @AutoGen.AgentExtension.RegisterPrintFormatMessageHook* to pretty print the message replied by the agent.

### Create coder agent

The code below shows how to create `coder` agent. `coder` agent is a dotnet coder who can write code to resolve tasks.

[!code-csharp[](../../sample/AutoGen.BasicSamples/Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs?name=create_coder)]

### Create reviewer agent

The code below shows how to create `reviewer` agent. `reviewer` agent is a dotnet code reviewer who can review code written by `coder`. In this example, a `function` is used to examine if the code written by `coder` follows the condition.

[!code-csharp[](../../sample/AutoGen.BasicSamples/Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs?name=reviewer_function)]

> [!TIP]
> You can use @AutoGen.FunctionAttribute to generate type-safe function definition and function call wrapper for the function. For more information, please check out [Create type safe function call](./Create-type-safe-function-call.md).

[!code-csharp[](../../sample/AutoGen.BasicSamples/Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs?name=create_reviewer)]

> [!TIP]
> You can use @AutoGen.MiddlewareExtension.RegisterPostProcess* to modify the behavior of an agent. For more information, please refer to [Middleware-agent](./Middleware-agent.md).
### Create runner agent

The code below shows how to create `runner` agent. `runner` agent is a dotnet code runner who can run code written by `coder` and print the result.

[!code-csharp[](../../sample/AutoGen.BasicSamples/Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs?name=create_runner)]

> [!TIP]
> You can use @AutoGen.MiddlewareExtension.RegisterPreProcess* and @AutoGen.MiddlewareExtension.RegisterReply* to modify the behavior of an agent. For more information, please refer to [Middleware-agent](./Middleware-agent.md).

> [!TIP]
> `AutoGen` provides a built-in support for running code snippet. For more information, please check out [Execute code snippet](./Run-dotnet-code.md).

> [!Warning]
> Running arbitrary code snippet from agent response could bring risks to your system. Using this feature with caution.

### Create group chat

The code below shows how to create a dynamic group chat with @AutoGen.GroupChat. In this example, we will create a dynamic group chat with 4 agents: `admin`, `coder`, `reviewer` and `runner`.

[!code-csharp[](../../sample/AutoGen.BasicSamples/Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs?name=create_group_chat)]

> [!TIP]
> You can set up initial context for the group chat using @AutoGen.GroupChatExtension.AddInitializeMessage*. The initial context can help group admin orchestrate the conversation flow.

### Start group chat

Then you can start the group chat by sending a message to group chat manager

[!code-csharp[](../../sample/AutoGen.BasicSamples/Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs?name=start_group_chat)]