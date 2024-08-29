## Overview of function call

In some LLM models, you can provide a list of function definitions to the model. The function definition is usually essentially an OpenAPI schema object which describes the function, its parameters and return value. And these function definitions tells the model what "functions" are available to be used to resolve the user's request. This feature greatly extend the capability of LLM models by enabling them to "execute" arbitrary function as long as it can be described as a function definition.

Below is an example of a function definition for getting weather report for a city:

> [!NOTE]
> To use function call, the underlying LLM model must support function call as well for the best experience.
> The model used in the example below is `gpt-3.5-turbo-0613`.
```json
{
    "name": "GetWeather",
    "description": "Get the weather report for a city",
    "parameters": {
        "city": {
            "type": "string",
            "description": "The city name"
        },
        "required": ["city"]
    },
}
```



When the model receives a message, it will intelligently decide whether to use function call or not based on the message received. If the model decides to use function call, it will generate a function call which can be used to invoke the actual function. The function call is a json object which contains the function name and its arguments.

Below is an example of a function call object for getting weather report for Seattle:

```json
{
    "name": "GetWeather",
    "arguments": {
        "city": "Seattle"
    }
}
```

And when the function call is return to the caller, it can be used to invoke the actual function to get the weather report for Seattle.

### Create type-safe function contract and function call wrapper use AutoGen.SourceGenerator
AutoGen provides a source generator to easness the trouble of manually craft function contract and function call wrapper from a function. To use this feature, simply add the `AutoGen.SourceGenerator` package to your project and decorate your function with `Function` attribute.

For more information, please check out [Create type-safe function](Create-type-safe-function-call.md).

### Use function call in an agent
AutoGen provides first-class support for function call in its agent story. Usually there are three ways to enable a function call in an agent.
- Pass function definitions when creating an agent. This only works if the agent supports pass function call from its constructor.
- Passing function definitions in @AutoGen.Core.GenerateReplyOptions when invoking an agent
- Register an agent with @AutoGen.Core.FunctionCallMiddleware to process and invoke function calls.

For more information, please check out [Use function call in an agent](Use-function-call.md).