# Multi-agent conversation Framework


AutoGen offers a unified multi-agent conversation framework as a high-level abstraction of using foundation models. It features capable, customizable and conversable agents which integrate LLM, tool and human via automated agent chat.
By automating chat among multiple capable agents, one can easily make them collectively perform tasks autonomously or with human feedback, including tasks that require using tools via code.

This framework simplifies the orchestration, automation and optimization of a complex LLM workflow. It maximizes the performance of LLM models and augments their weakness. It enables building next-gen LLM applications based on multi-agent conversations with minimal effort.

### Conversable Agents

We have designed a generic `ResponsiveAgent` class for Agents that are capable of conversing with each other through the exchange of messages to jointly finish a task. An agent can communicate with other agents and perform actions. Different agents can differ in what actions they perform after receiving messages. Two representative subclasses are `AssistantAgent` and `UserProxyAgent`.

- `AssistantAgent`. Designed to act as an assistant by responding to user requests. It could write Python code (in a Python coding block) for a user to execute when a message (typically a description of a task that needs to be solved) is received. Under the hood, the Python code is written by LLM (e.g., GPT-4). It can also receive the execution results and suggest code with bug fix. Its behavior can be altered by passing a new system message. The LLM [inference](#enhanced-inference) configuration can be configured via `llm_config`.
- `UserProxyAgent`. Serves as a proxy for the human user. Upon receiving a message, the UserProxyAgent will either solicit the human user's input or prepare an automatically generated reply. The chosen action depends on the settings of the `human_input_mode` and `max_consecutive_auto_reply` when the `UserProxyAgent` instance is constructed, and whether a human user input is available.
By default, the automatically generated reply is crafted based on automatic code execution. The `UserProxyAgent` triggers code execution automatically when it detects an executable code block in the received message and no human user input is provided. Code execution can be disabled by setting `code_execution_config` to False. LLM-based response is disabled by default. It can be enabled by setting `llm_config` to a dict corresponding to the [inference](#enhanced-inference) configuration.
When `llm_config` is set to a dict, `UserProxyAgent` can generate replies using an LLM when code execution is not performed.

The auto-reply capability of `ResponsiveAgent` allows for more autonomous multi-agent communication while retaining the possibility of human intervention.
One can also easily extend it by registering auto_reply functions with the `register_auto_reply()` method.

## Multi-agent Conversations

### Basic Example

Example usage of the agents to solve a task with code:
```python
from pyautogen import AssistantAgent, UserProxyAgent

# create an AssistantAgent instance named "assistant"
assistant = AssistantAgent(name="assistant")

# create a UserProxyAgent instance named "user_proxy"
user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",  # in this mode, the agent will never solicit human input but always auto reply
)

# the assistant receives a message from the user, which contains the task description
user.initiate_chat(
    assistant,
    message="""What date is today? Which big tech stock has the largest year-to-date gain this year? How much is the gain?""",
)
```
In the example above, we create an AssistantAgent named "assistant" to serve as the assistant and a UserProxyAgent named "user_proxy" to serve as a proxy for the human user.
1. The assistant receives a message from the user_proxy, which contains the task description.
2. The assistant then tries to write Python code to solve the task and sends the response to the user_proxy.
3. Once the user_proxy receives a response from the assistant, it tries to reply by either soliciting human input or preparing an automatically generated reply. In this specific example, since `human_input_mode` is set to `"NEVER"`, the user_proxy will not solicit human input but send an automatically generated reply (auto reply). More specifically, the user_proxy executes the code and uses the result as the auto-reply.
4. The assistant then generates a further response for the user_proxy. The user_proxy can then decide whether to terminate the conversation. If not, steps 3 and 4 are repeated.

Please find a visual illustration of how UserProxyAgent and AssistantAgent collaboratively solve the above task below:
![Agent Chat Example](images/agent_example.png)

### Human Input Mode

The `human_input_mode` parameter of `UserProxyAgent` controls the behavior of the agent when it receives a message. It can be set to `"NEVER"`, `"ALWAYS"`, or `"TERMINATE"`.
- Under the mode `human_input_mode="NEVER"`, the multi-turn conversation between the assistant and the user_proxy stops when the number of auto-reply reaches the upper limit specified by `max_consecutive_auto_reply` or the received message is a termination message according to `is_termination_msg`.
- When `human_input_mode` is set to `"ALWAYS"`, the user proxy agent solicits human input every time a message is received; and the conversation stops when the human input is "exit", or when the received message is a termination message and no human input is provided.
- When `human_input_mode` is set to `"TERMINATE"`, the user proxy agent solicits human input only when a termination message is received or the number of auto replies reaches `max_consecutive_auto_reply`.

### Function Calling
To leverage [function calling capability of OpenAI's Chat Completions API](https://openai.com/blog/function-calling-and-other-api-updates?ref=upstract.com), one can pass in a list of callable functions or class methods to `UserProxyAgent`, which corresponds to the description of functions passed to OpenAI's API.

Example usage of the agents to solve a task with function calling feature:
```python
from pyautogen import AssistantAgent, UserProxyAgent

# put the descriptions of functions in config to be passed to OpenAI's API
llm_config = {
    "model": "gpt-4-0613",
    "functions": [
        {
            "name": "python",
            "description": "run cell in ipython and return the execution result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cell": {
                        "type": "string",
                        "description": "Valid Python cell to execute.",
                    }
                },
                "required": ["cell"],
            },
        },
        {
            "name": "sh",
            "description": "run a shell script and return the execution result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Valid shell script to execute.",
                    }
                },
                "required": ["script"],
            },
        },
    ],
}

# create an AssistantAgent instance named "assistant"
chatbot = AssistantAgent("assistant", **llm_config)

# create a UserProxyAgent instance named "user_proxy"
user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
)

# define functions according to the function desription
from IPython import get_ipython

def exec_python(cell):
    ipython = get_ipython()
    result = ipython.run_cell(cell)
    log = str(result.result)
    if result.error_before_exec is not None:
        log += f"\n{result.error_before_exec}"
    if result.error_in_exec is not None:
        log += f"\n{result.error_in_exec}"
    return log

def exec_sh(script):
    return user_proxy.execute_code_blocks([("sh", script)])

# register the functions
user_proxy.register_function(
    function_map={
        "python": exec_python,
        "sh": exec_sh,
    }
)

# start the conversation
user_proxy.initiate_chat(
    chatbot,
    message="Draw two agents chatting with each other with an example dialog.",
)
```

### Notebook Examples

*Interested in trying it yourself? Please check the following notebook examples:*
* [Automated Task Solving with Code Generation, Execution & Debugging](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_auto_feedback_from_code_execution.ipynb)
* [Auto Code Generation, Execution, Debugging and Human Feedback](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_human_feedback.ipynb)
* [Solve Tasks Requiring Web Info](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_web_info.ipynb)
* [Use Provided Tools as Functions](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_function_call.ipynb)
* [Automated Task Solving with Coding & Planning Agents](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_planning.ipynb)
* [Automated Task Solving with GPT-4 + Multiple Human Users](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_two_users.ipynb)
* [Automated Chess Game Playing & Chitchatting by GPT-4 Agents](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_chess.ipynb)
* [Automated Task Solving by Group Chat](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_groupchat.ipynb)
* [Automated Continual Learning from New Data](https://github.com/microsoft/autogen/blob/main/notebook/autogen_agentchat_stream.ipynb)




## For Further Reading

*Interested in the research that leads to this package? Please check the following papers.*

* [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework](https://arxiv.org/abs/2308.08155) Qingyun Wu, Gagan Bansal, Jieyu Zhang, Yiran Wu, Shaokun Zhang, Erkang Zhu, Beibin Li, Li Jiang, Xiaoyun Zhang and Chi Wang. ArXiv 2023.
