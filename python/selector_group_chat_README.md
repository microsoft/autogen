# SelectorGroupChat: How Does it Work?

SelectorGroupChat is a group chat similar to RoundRobinGroupChat, but with a model-based next speaker selection mechanism. When the team receives a task through `run()` or `run_stream()`, the following steps are executed:

1. The team analyzes the current conversation context, including the conversation history and participants’ name and description attributes, to determine the next speaker using a model. By default, the team will not select the same speaker consecutively unless it is the only agent available. This can be changed by setting `allow_repeated_speaker=True`. You can also override the model by providing a custom selection function.
2. The team prompts the selected speaker agent to provide a response, which is then broadcasted to all other participants.
3. The termination condition is checked to determine if the conversation should end; if not, the process repeats from step 1.
4. When the conversation ends, the team returns the `TaskResult` containing the conversation history from this task.
5. Once the team finishes the task, the conversation context is kept within the team and all participants, so the next task can continue from the previous conversation context. You can reset the conversation context by calling `reset()`.

## Example: Web Search/Analysis

This example demonstrates how to use SelectorGroupChat with specialized agents for a web search and data analysis task. See `selector_group_chat_example.py` for the full code.

### Agents
- **Planning Agent**: The strategic coordinator that breaks down complex tasks into manageable subtasks.
- **Web Search Agent**: An information retrieval specialist that interfaces with the `search_web_tool`.
- **Data Analyst Agent**: An agent specialist in performing calculations equipped with `percentage_change_tool`.

The tools `search_web_tool` and `percentage_change_tool` are external tools that the agents can use to perform their tasks.

### Example Task
Analyze the percentage change in total rebounds for Dwayne Wade between the 2007-2008 and 2008-2009 Miami Heat seasons.

### Key Points
- Agents' `name` and `description` attributes are used by the model to determine the next speaker.
- By default, the same agent is not selected consecutively unless only one agent is available.
- The conversation context is preserved for subsequent tasks unless reset.

---

**Note:** By default, `AssistantAgent` returns the tool output as the response. If your tool does not return a well-formed string in natural language format, you may want to add a reflection step within the agent by setting `reflect_on_tool_use=True` when creating the agent. This will allow the agent to reflect on the tool output and provide a natural language response.
