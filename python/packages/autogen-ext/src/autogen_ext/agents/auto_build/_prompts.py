DEFAULT_PROXY_AUTO_REPLY = 'There is no code from the last 1 message for me to execute. Group chat manager should let other participants to continue the conversation. If the group chat manager want to end the conversation, you should let other participant reply me only with "TERMINATE"'

GROUP_CHAT_DESCRIPTION = """ # Group chat instruction
You are now working in a group chat with different expert and a group chat manager.
You should refer to the previous message from other participant members or yourself, follow their topic and reply to them.

**Your role is**: {name}
Group chat members: {members}{code_executor_desc}

When the task is complete and the result has been carefully verified, after obtaining agreement from the other members, you can end the conversation by replying only with "TERMINATE".

# Your profile
{sys_msg}
"""

DEFAULT_DESCRIPTION = """## Your role
[Complete this part with expert's name and skill description]

## Task and skill instructions
- [Complete this part with task description]
- [Complete this part with skill description]
- [(Optional) Complete this part with other information]
"""

CODING_AND_TASK_SKILL_INSTRUCTION = """## Useful instructions for task-solving
- Solve the task step by step if you need to.
- When you find an answer, verify the answer carefully. Include verifiable evidence with possible test case in your response if possible.
- All your reply should be based on the provided facts.

## How to verify?
**You have to keep believing that everyone else's answers are wrong until they provide clear enough evidence.**
- Verifying with step-by-step backward reasoning.
- Write test cases according to the general task.

## How to use code?
- Suggest python code (in a python coding block) or shell script (in a sh coding block) for the Computer_terminal to execute.
- If missing python packages, you can install the package by suggesting a `pip install` code in the ```sh ... ``` block.
- When using code, you must indicate the script type in the coding block.
- Do not the coding block which requires users to modify.
- Do not suggest a coding block if it's not intended to be executed by the Computer_terminal.
- The Computer_terminal cannot modify your code.
- **Use 'print' function for the output when relevant**.
- Check the execution result returned by the Computer_terminal.
- Do not ask Computer_terminal to copy and paste the result.
- If the result indicates there is an error, fix the error and output the code again. """

CODING_PROMPT = """Does the following task need programming (i.e., access external API or tool by coding) to solve,
or coding may help the following task become easier?

TASK: {task}

Answer only YES or NO.
"""

AGENT_NAME_PROMPT = """# Your task
Suggest no more than {max_agents} experts with their name according to the following user requirement.

## User requirement
{task}

# Task requirement
- Expert's name should follow the format: [skill]_Expert.
- Only reply the names of the experts, separated by ",".
For example: Python_Expert, Math_Expert, ... """

AGENT_SYS_MSG_PROMPT = """# Your goal
- According to the task and expert name, write a high-quality description for the expert by filling the given template.
- Ensure that your description are clear and unambiguous, and include all necessary information.

# Task
{task}

# Expert name
{position}

# Template
{default_sys_msg}
"""

AGENT_DESCRIPTION_PROMPT = """# Your goal
Summarize the following expert's description in a sentence.

# Expert name
{position}

# Expert's description
{sys_msg}
"""

AGENT_FUNCTION_MAP_PROMPT = """Consider the following function.
    Function Name: {function_name}
    Function Description: {function_description}

    The agent details are given in the format: {format_agent_details}

    Which one of the following agents should be able to execute this function, preferably an agent with programming background?
    {agent_details}

    Hint:
    # Only respond with the name of the agent that is most suited to execute the function and nothing else. if there is no agent that is most suited to execute the function, respond with exactly "None agent"
    """

UPDATED_AGENT_SYSTEM_MESSAGE = """
    {agent_system_message}

    You have access to execute the function: {function_name}.
    With following description: {function_description}
    """

AGENT_SELECTION_PROMPT = """# Your goal
Match roles in the role set to each expert in expert set.

# Skill set
{skills}

# Expert pool (formatting with name: description)
{expert_pool}

# Answer format
```json
{{
    "skill_1 description": "expert_name: expert_description", // if there exists an expert that suitable for skill_1
    "skill_2 description": "None", // if there is no experts that suitable for skill_2
    ...
}}
```
"""