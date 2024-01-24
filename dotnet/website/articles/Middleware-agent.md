@AutoGen.MiddlewareAgent is a special agent in AutoGen. It allows you to override the behavior of an agent by adding middleware delegate function(s). In the middleware delegate function, you can do various things, such as logging/monitoring, modifying the agent reply, short-cut the next middleware etc. When multiple middleware functions are registered, the order of middleware functions is first registered, last invoked.

> [!NOTE]
> When multiple middleware functions are registered, the order of middleware functions is first registered, last invoked.

> [!TIP]
> To short-cut the next middleware, simply don't call the `next` parameter (see example below).

## Usage
### Create a middleware agent
The following code snippet shows how to create a middleware agent on top of an existing agent.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=code_snippet_1)]

### Register middleware function
The following code snippet shows how to register middleware functions to a middleware agent using @AutoGen.MiddlewareExtension.Use*.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=code_snippet_2)]

> [!NOTE]
> @AutoGen.MiddlewareExtension.Use* adds middleware to the agent itself. To avoid modifying the original agent, use @AutoGen.MiddlewareExtension.RegisterMiddleware* instead.

### Register multiple middleware functions
The following code snippet shows the calling order when multiple middleware functions are registered. The middleware 1 will be invoked first, then middleware 0, and finally the original agent.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=code_snippet_3)]

### Short-cut the middleware
To short-cut the next middleware, simply don't call the `next` parameter.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=code_snippet_4)]

## Examples
Here're a few examples of where you might want to use middleware agent.
### Example 1: Logging to console
The following code snippet shows how to use middleware agent to log the conversation history and agent reply to console.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=code_snippet_logging_to_console)]

> [!NOTE]
> Use @AutoGen.MiddlewareExtension.RegisterMiddleware* to avoid modifying the original agent.

> [!TIP]
> AutoGen provides a built-in @AutoGen.MiddlewareExtension.RegisterPrintFormatMessageHook* to print the reply message nicely in console.

### Example 2: response format forcement
The following code snippet shows how to use middleware agent to force the agent to reply with json format and fix the reply if json is malformed.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/MiddlewareAgentCodeSnippet.cs?name=code_snippet_response_format_forcement)]

## See also
In @AutoGen.MiddlewareExtension, AutoGen provides a series of short-cuts APIs to create middleware agent on top of an existing agent.
- @AutoGen.MiddlewareExtension.RegisterMiddleware*
- @AutoGen.MiddlewareExtension.RegisterPreProcess*
- @AutoGen.MiddlewareExtension.RegisterPostProcess*
- @AutoGen.MiddlewareExtension.RegisterReply*