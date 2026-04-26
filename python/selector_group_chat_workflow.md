# SelectorGroupChat Workflow and Termination Conditions

This document describes the workflow and configuration for SelectorGroupChat, including agent selection, task assignment, and termination conditions.

## Workflow
1. **Task Reception**: SelectorGroupChat receives a task and, based on agent descriptions, selects the most appropriate agent to handle the initial task (typically the Planning Agent).
2. **Planning**: The Planning Agent analyzes the task and breaks it down into subtasks, assigning each to the most appropriate agent using the format: `<agent> : <task>`.
3. **Dynamic Selection**: SelectorGroupChat dynamically selects the next agent to handle their assigned subtask based on conversation context and agent descriptions.
4. **Web Search**: The Web Search Agent performs searches one at a time, storing results in the shared conversation history.
5. **Data Analysis**: The Data Analyst processes the gathered information using available calculation tools when selected.
6. **Iteration**: The workflow continues with agents being dynamically selected until either:
    - The Planning Agent determines all subtasks are complete and sends "TERMINATE"
    - An alternative termination condition is met (e.g., a maximum number of messages)

**Tip:** When defining your agents, include a helpful description since this is used to decide which agent to select next.

## Termination Conditions
We use two termination conditions:
- `TextMentionTermination` to end the conversation when the Planning Agent sends "TERMINATE"
- `MaxMessageTermination` to limit the conversation to 25 messages

Example:

```python
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination

text_mention_termination = TextMentionTermination("TERMINATE")
max_messages_termination = MaxMessageTermination(max_messages=25)
termination = text_mention_termination | max_messages_termination
```

## Selector Prompt
SelectorGroupChat uses a model to select the next speaker based on the conversation context. Use a custom selector prompt to align with the workflow:

```python
selector_prompt = """Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
Make sure the planner agent has assigned tasks before other agents start working.
Only select one agent.
"""
```

**String variables available in the selector prompt:**
- `{participants}`: The names of candidates for selection. Format: `["<name1>", "<name2>", ...]`.
- `{roles}`: A newline-separated list of names and descriptions of the candidate agents. Format: `"<name> : <description>"` per line.
- `{history}`: The conversation history formatted as a double newline separated list of names and message content. Format: `"<name> : <message content>"` per message.

**Tip:**
- Do not overload the model with too much instruction in the selector prompt.
- For powerful models (e.g., GPT-4o), you can use more detailed prompts. For smaller models, keep the prompt simple.
- If you need multiple conditions for each agent, consider a custom selection function or breaking down the task into smaller, sequential tasks.
