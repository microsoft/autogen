---
myst:
  html_meta:
    "description lang=en": |
      Usage for AutoGen Studio - A low code tool for building and debugging multi-agent systems
---

# Usage

AutoGen Studio (AGS) provides a Team Builder interface where developers can define multiple components and behaviors. Users can create teams, add agents to teams, attach tools and models to agents, and define team termination conditions.
After defining a team, users can test directly in the team builder view or attach it to a session for use in the Playground view.

> See a video tutorial on AutoGen Studio v0.4 (02/25) - [https://youtu.be/oum6EI7wohM](https://youtu.be/oum6EI7wohM)

[![A Friendly Introduction to AutoGen Studio v0.4](https://img.youtube.com/vi/oum6EI7wohM/maxresdefault.jpg)](https://www.youtube.com/watch?v=oum6EI7wohM)

## Setting Up an API Key

Most of your agents will require an API key. You can set up an environment variable `OPENAI_API_KEY` (assuming you are using OpenAI models) and AutoGen will automatically use this for any OpenAI model clients you specify for your agents or teams. Alternatively you can specify the api key as part of the team or agent configuration.

See the section below on how to build an agent team either using the visual builder or by directly editing the JSON configuration.

## Building an Agent Team

<br/>

AutoGen Studio integrates closely with all component abstractions provided by AutoGen AgentChat, including {py:class}`~autogen_agentchat.teams`, {py:class}`~autogen_agentchat.agents`, {py:class}`~autogen_core.models`, {py:class}`~autogen_core.tools`, and termination {py:class}`~autogen_agentchat.conditions`.

The Team Builder view in AGS provides a visual team builder that allows users to define components through either drag-and-drop functionality or by editing a JSON configuration of the team directly.

### Using the Visual Builder

The visual builder is enabled by default and allows users to drag-and-drop components from the provided Component library to the Team Builder canvas. The team builder canvas represents a team and consists of a main team node and a set of a connected agent nodes. It includes a Component Library that has a selection of components that can be added to the team or agent nodes in the canvas.

![Team Builder](teambuilder.jpg)

The core supported behaviours include:

- Create a new team. This can be done by clicking on the "New Team" button in the Team Builder view or by selecting any of the existing default teams that ship with the default AGS Gallery. Once you do this, a new team node and agent node(s) will be created in the canvas.
- Drag and drop components from the library to the team or agent nodes in the canvas.
  - Teams: drag in agents and termination conditions to the team node (there are specific drop zones for these components)
  - Agents: drag in models and tools to the agent node (there are specific drop zones for these components)
- Editing Team/Agent Nodes: Click on the edit icon (top right) of the node to view and edit its properties. This pops up a panel that allows you to edit the fields of the node. In some cases you will need to scroll down and click into specific sections e.g., for an agent with a model client, you will need to click into the model client section to edit the model client properties. Once done with editing, click on the save button to save the changes.

### Using the JSON Editor

![JSON Editor](jsoneditor.jpg)

AGS also lets you directly modify the JSON configuration of the team. This can be done by toggling the visual builder mode off. Once you do this, you will see the JSON configuration of the team. You can then edit the JSON configuration directly.

> Did you know that you define your agents in Python, export them to JSON and then paste them in the JSON editor? The section below shows how to accomplish this.

## Declarative Specification of Componenents

AutoGen Studio is built on the declarative specification behaviors of AutoGen AgentChat. This allows users to define teams, agents, models, tools, and termination conditions in Python and then dump them into a JSON file for use in AutoGen Studio.

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

This example shows a team with a single agent, using the `RoundRobinGroupChat` type and a `TextMentionTermination` condition. You will also notice that the model client is an `OpenAIChatCompletionClient` model client where only the model name is specified. In this case, the API key is assumed to be set as an environment variable `OPENAI_API_KEY`. You can also specify the API key as part of the model client configuration.

To understand the full configuration of an model clients, you can refer to the [AutoGen Model Clients documentation](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/components/model-clients.html).

Note that you can similarly define your model client in Python and call `dump_component()` on it to get the JSON configuration and use it to update the model client section of your team or agent configuration.

Finally, you can use the `load_component()` method to load a team configuration from a JSON file:

```python

import json
from autogen_agentchat.teams import BaseGroupChat
team_config = json.load(open("team.json"))
team = BaseGroupChat.load_component(team_config)

```

## Gallery - Sharing and Reusing Components

AGS provides a Gallery view, where a gallery is a collection of components - teams, agents, models, tools, and terminations - that can be shared and reused across projects.

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
result_stream = tm.run(task="What is the weather in New York?", team_config="team.json") # or tm.run_stream(..)
```

To export team configurations, use the export button in Team Builder to generate a JSON file for Python application use.
