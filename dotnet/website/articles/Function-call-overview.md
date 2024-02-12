## Overview of function call

In some LLM models, you can provide a list of function definitions to the model. The function definition is usually essentially an OpenAPI schema object which describes the function, its parameters and return value. And these function definitions tells the model what "functions" are available to be used to resolve the user's request. This feature greatly extend the capability of LLM models by enabling them to "execute" arbitrary function as long as it can be described as a function definition.

Below is an example of a function definition for getting weather report for a city:

```json
llm: gpt-3.5-turbo-0613

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
llm: gpt-3.5-turbo-0613

{
    "name": "GetWeather",
    "arguments": {
        "city": "Seattle"
    }
}
```

And when the function call is return to the caller, it can be used to invoke the actual function to get the weather report for Seattle.

## Overview of function call in AutoGen
AutoGen provides first-class support for function call its agent story. To consume function call in AutoGen, you can either pass function definitions when creating an agent, or passing function definitions in @AutoGen.GenerateReplyOptions when invoking an agent. AutoGen also allows you to decide how to invoke the function call from an agent. You can return the function call as-is, invoking the function call inside the agent, or invoking the function call by another agent. Besides, AutoGen also provides a source generator to generate type-safe function definition and function call wrapper from a function. This feature greatly simplifies the process of manual crafting function definition and function call wrapper from a function, which is usually a tedious and error-prone process.

Below is the link to the detailed documentation of function call in AutoGen:
- [Define type-safe function definition and function call wrapper](Create-type-safe-function-call.md)
- [Use function call in an agent](Use-function-call.md)