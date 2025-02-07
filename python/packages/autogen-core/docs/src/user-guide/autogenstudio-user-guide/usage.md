---
myst:
  html_meta:
    "description lang=en": |
      Usage for AutoGen Studio - A low code tool for building and debugging multi-agent systems
---

# Usage

AutoGen Studio provides a Team Builder interface where developers can define multiple components and behaviors. Users can create teams, add agents to teams, attach tools and models to agents, and define team termination conditions.
After defining a team, users can test it in the Playground view to accomplish various tasks through direct interaction.

![AutoGen Studio](https://media.githubusercontent.com/media/microsoft/autogen/refs/heads/main/python/packages/autogen-studio/docs/ags_screen.png)

## Declarative Specification of Componenents

AutoGen Studio is built on the declarative specification behaviors of AutoGen AgentChat. This allows users to define teams, agents, models, tools, and termination conditions in python and then dump them into a JSON file for use in AutoGen Studio.

Here's an example of an agent team and how it is converted to a JSON file:

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import  TextMentionTermination

agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-mini",
        ),
    )

agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
config = agent_team.dump_component()
print(config.model_dump_json())
```

```json
{
  "provider": "autogen_agentchat.teams.RoundRobinGroupChat",
  "component_type": "team",
  "version": 1,
  "component_version": 1,
  "description": "A team that runs a group chat with participants taking turns in a round-robin fashion\n    to publish a message to all.",
  "label": "RoundRobinGroupChat",
  "config": {
    "participants": [
      {
        "provider": "autogen_agentchat.agents.AssistantAgent",
        "component_type": "agent",
        "version": 1,
        "component_version": 1,
        "description": "An agent that provides assistance with tool use.",
        "label": "AssistantAgent",
        "config": {
          "name": "weather_agent",
          "model_client": {
            "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
            "component_type": "model",
            "version": 1,
            "component_version": 1,
            "description": "Chat completion client for OpenAI hosted models.",
            "label": "OpenAIChatCompletionClient",
            "config": { "model": "gpt-4o-mini" }
          },
          "tools": [],
          "handoffs": [],
          "model_context": {
            "provider": "autogen_core.model_context.UnboundedChatCompletionContext",
            "component_type": "chat_completion_context",
            "version": 1,
            "component_version": 1,
            "description": "An unbounded chat completion context that keeps a view of the all the messages.",
            "label": "UnboundedChatCompletionContext",
            "config": {}
          },
          "description": "An agent that provides assistance with ability to use tools.",
          "system_message": "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
          "model_client_stream": false,
          "reflect_on_tool_use": false,
          "tool_call_summary_format": "{result}"
        }
      }
    ],
    "termination_condition": {
      "provider": "autogen_agentchat.conditions.TextMentionTermination",
      "component_type": "termination",
      "version": 1,
      "component_version": 1,
      "description": "Terminate the conversation if a specific text is mentioned.",
      "label": "TextMentionTermination",
      "config": { "text": "TERMINATE" }
    }
  }
}
```

This example shows a team with a single agent, using the `RoundRobinGroupChat` type and a `TextMentionTermination` condition.

## Building an Agent Team

<div style="padding:58.13% 0 0 0;position:relative; border-radius:5px; border-bottom:10px"><iframe src="https://player.vimeo.com/video/1043133833?badge=0&amp;autopause=0&amp;player_id=0&amp;app_id=58479" frameborder="0" allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media" style="position:absolute;top:0;left:0;width:100%;height:100%;" title="AutoGen Studio v0.4x - Drag and Drop Interface"></iframe></div><script src="https://player.vimeo.com/api/player.js"></script>

<br/>

AutoGen Studio integrates closely with all component abstractions provided by AutoGen AgentChat, including {py:class}`~autogen_agentchat.teams`, {py:class}`~autogen_agentchat.agents`, {py:class}`~autogen_core.models`, {py:class}`~autogen_core.tools`, and termination {py:class}`~autogen_agentchat.conditions`.

The Team Builder interface allows users to define components through either declarative specification or drag-and-drop functionality:

Team Builder Operations:

- Create a new team
  - Edit Team JSON directly (toggle visual builder mode off) or
  - Use the visual builder, drag-and-drop components from the library:
    - Teams: Add agents and termination conditions
    - Agents: Add models and tools
- Save team configurations

## Gallery - Sharing and Reusing Components

A Gallery is a collection of components - teams, agents, models, tools, and terminations - that can be shared and reused across projects.

Users can create a local gallery or import a gallery (from a URL, a JSON file import or simply by copying and pasting the JSON). At any given time, users can select any of the current Gallery items as a **default gallery**. This **default gallery** will be used to populate the Team Builder sidebar with components.

- Create new galleries via Gallery -> New Gallery
- Edit gallery JSON as needed
- Set a **default** gallery (click pin icon in sidebar) to make components available in Team Builder.

## Interactively Running Teams

The AutoGen Studio Playground enables users to:

- Test teams on specific tasks
- Review generated artifacts (images, code, text)
- Monitor team "inner monologue" during task execution
- View performance metrics (turn count, token usage)
- Track agent actions (tool usage, code execution results)

## Importing and Reusing Team Configurations

AutoGen Studio's Gallery view offers a default component collection and supports importing external configurations:

- Create/Import galleries through Gallery -> New Gallery -> Import
- Set default galleries via sidebar pin icon
- Access components in Team Builder through Sidebar -> From Gallery

### Python Integration

Team configurations can be integrated into Python applications using the `TeamManager` class:

```python
from autogenstudio.teammanager import TeamManager

tm = TeamManager()
result_stream = tm.run(task="What is the weather in New York?", team_config="team.json") # or wm.run_stream(..)
```

To export team configurations, use the export button in Team Builder to generate a JSON file for Python application use.
