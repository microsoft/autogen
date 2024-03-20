# Together AI
This cloud-based proxy server example, using [together.ai](https://www.together.ai/), is a group chat between a Python developer
and a code reviewer, who are given a coding task.

Start by [installing AutoGen](/docs/installation/) and getting your [together.ai API key](https://api.together.xyz/settings/profile).

Put your together.ai API key in an environment variable, TOGETHER_API_KEY.

Linux / Mac OSX:

```bash
export TOGETHER_API_KEY=YourTogetherAIKeyHere
```

Windows (command prompt):

```powershell
set TOGETHER_API_KEY=YourTogetherAIKeyHere
```

Create your LLM configuration, with the [model you want](https://docs.together.ai/docs/inference-models).

```python
import autogen
import os

llm_config={
    "config_list": [
        {
            # Available together.ai model strings:
            # https://docs.together.ai/docs/inference-models
            "model": "mistralai/Mistral-7B-Instruct-v0.1",
            "api_key": os.environ['TOGETHER_API_KEY'],
            "base_url": "https://api.together.xyz/v1"
        }
    ],
    "cache_seed": 42
}
```

## Construct Agents

```python
# User Proxy will execute code and finish the chat upon typing 'exit'
user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    system_message="A human admin",
    code_execution_config={
        "last_n_messages": 2,
        "work_dir": "groupchat",
        "use_docker": False,
    },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    human_input_mode="TERMINATE",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
)

# Python Coder agent
coder = autogen.AssistantAgent(
    name="softwareCoder",
    description="Software Coder, writes Python code as required and reiterates with feedback from the Code Reviewer.",
    system_message="You are a senior Python developer, a specialist in writing succinct Python functions.",
    llm_config=llm_config,
)

# Code Reviewer agent
reviewer = autogen.AssistantAgent(
    name="codeReviewer",
    description="Code Reviewer, reviews written code for correctness, efficiency, and security. Asks the Software Coder to address issues.",
    system_message="You are a Code Reviewer, experienced in checking code for correctness, efficiency, and security. Review and provide feedback to the Software Coder until you are satisfied, then return the word TERMINATE",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    llm_config=llm_config,
)
```

## Establish the group chat

```python
# Establish the Group Chat and disallow a speaker being selected consecutively
groupchat = autogen.GroupChat(agents=[user_proxy, coder, reviewer], messages=[], max_round=12, allow_repeat_speaker=False)

# Manages the group of multiple agents
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
```

## Start Chat

```python
# Start the chat with a request to write a function
user_proxy.initiate_chat(
    manager,
    message="Write a Python function for the Fibonacci sequence, the function will have one parameter for the number in the sequence, which the function will return the Fibonacci number for."
)
# type exit to terminate the chat
```

Output:
```` text
UserProxy (to chat_manager):

Write a Python function for the Fibonacci sequence, the function will have one parameter for the number in the sequence, which the function will return the Fibonacci number for.

--------------------------------------------------------------------------------
softwareCoder (to chat_manager):

 Sure, here is a simple Python function that uses recursion to calculate the Fibonacci number:

```python
def fibonacci(n):
    if n <= 0:
        return "Input should be a positive integer."
    elif n == 1:
        return 0
    elif n == 2:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
```

This function takes an integer `n` as input and returns the `n`th number in the Fibonacci sequence. The Fibonacci sequence is a series of numbers in which each number is the sum of the two preceding ones, usually starting with 0 and 1.

Note that this implementation uses recursion and may not be efficient for large values of `n`. In such cases, an iterative approach or memoization would be more appropriate.

--------------------------------------------------------------------------------
codeReviewer (to chat_manager):

 I see a couple of issues with the current implementation of the `fibonacci` function:

1. The function does not handle negative inputs correctly. Currently, it returns a string message for any input less than or equal to 0. It would be better to raise a `ValueError` or return a more informative message.
2. The function uses recursion to calculate the Fibonacci number, which can be inefficient for large inputs. A more efficient approach would be to use an iterative approach or memoization.

Here's an updated implementation that addresses these issues:

```python
def fibonacci(n):
    if n <= 0:
        raise ValueError("Input should be a positive integer.")
    elif n == 1:
        return 0
    elif n == 2:
        return 1
    else:
        a, b = 0, 1
        for _ in range(n - 2):
            a, b = b, a + b
        return b
```

This implementation uses a loop to calculate the Fibonacci number iteratively, which is more efficient than the recursive approach. It also raises a `ValueError` for negative inputs, which is a more appropriate way to handle invalid inputs.

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...

>>>>>>>> EXECUTING CODE BLOCK 0 (inferred language is python)...
UserProxy (to chat_manager):

exitcode: 0 (execution succeeded)
Code output:


--------------------------------------------------------------------------------
codeReviewer (to chat_manager):

 I'm glad the updated implementation addresses the issues with the original code. Let me know if you have any further questions or if there's anything else I can help you with.

To terminate the conversation, please type "TERMINATE".

--------------------------------------------------------------------------------
Please give feedback to chat_manager. Press enter or type 'exit' to stop the conversation: exit
````
