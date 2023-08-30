## Utilities for Applications
AutoGen provides a drop-in replacement of `openai.Completion` or `openai.ChatCompletion` as an enhanced inference API. It allows easy performance tuning, utilities like API unification & caching, and advanced usage patterns, such as error handling, multi-config inference, context programming etc.

### Code

[`pyautogen.code_utils`](/docs/reference/autogen/code_utils) offers code-related utilities, such as:
- a [`improve_code`](/docs/reference/autogen/code_utils#improve_code) function to improve code for a given objective.
- a [`generate_assertions`](/docs/reference/autogen/code_utils#generate_assertions) function to generate assertion statements from function signature and docstr.
- a [`implement`](/docs/reference/autogen/code_utils#implement) function to implement a function from a definition.
- a [`eval_function_completions`](/docs/reference/autogen/code_utils#eval_function_completions) function to evaluate the success of a function completion task, or select a response from a list of responses using generated assertions.

### Math

[`pyautogen.math_utils`](/docs/reference/autogen/math_utils) offers utilities for math problems, such as:
- a [eval_math_responses](/docs/reference/autogen/math_utils#eval_math_responses) function to select a response using voting, and check if the final answer is correct if the canonical solution is provided.
