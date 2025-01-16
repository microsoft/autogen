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

AutoGen Studio uses a declarative specification system to build its GUI components. At runtime, the AGS API loads these specifications into AutoGen AgentChat objects to address tasks.

Here's an example of a declarative team specification:

```json
{
  "version": "1.0.0",
  "component_type": "team",
  "name": "sample_team",
  "participants": [
    {
      "component_type": "agent",
      "name": "assistant_agent",
      "agent_type": "AssistantAgent",
      "system_message": "You are a helpful assistant. Solve tasks carefully. When done respond with TERMINATE",
      "model_client": {
        "component_type": "model",
        "model": "gpt-4o-2024-08-06",
        "model_type": "OpenAIChatCompletionClient"
      },
      "tools": []
    }
  ],
  "team_type": "RoundRobinGroupChat",
  "termination_condition": {
    "component_type": "termination",
    "termination_type": "MaxMessageTermination",
    "max_messages": 3
  }
}
```

This example shows a team with a single agent, using the `RoundRobinGroupChat` type and a `MaxMessageTermination` condition limited to 3 messages.

```{note}
Work is currently in progress to make the entire AgentChat API declarative. This will allow all agentchat components to be `dumped` into the same declarative specification format used by AGS.
```

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
