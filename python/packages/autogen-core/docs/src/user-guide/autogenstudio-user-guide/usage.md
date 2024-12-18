---
myst:
  html_meta:
    "description lang=en": |
      Usage for AutoGen Studio - A low code tool for building and debugging multi-agent systems
---

# Usage

The expected usage behavior is that developers use the provided Team Builder interface to to define teams - create agents, attach tools and models to agents, and define termination conditions. Once the team is defined, users can run the team in the Playground to interact with the team to accomplish tasks.

![AutoGen Studio](https://media.githubusercontent.com/media/microsoft/autogen/refs/heads/main/python/packages/autogen-studio/docs/ags_screen.png)

## Building an Agent Team

AutoGen Studio is tied very closely with all of the component abstractions provided by AutoGen AgentChat. This includes - {py:class}`~autogen_agentchat.teams`, {py:class}`~autogen_agentchat.agents`, {py:class}`~autogen_core.models`, {py:class}`~autogen_core.tools`, termination {py:class}`~autogen_agentchat.conditions`.

Users can define these components in the Team Builder interface either via a declarative specification or by dragging and dropping components from a component library.

## Interactively Running Teams

AutoGen Studio Playground allows users to interactively test teams on tasks and review resulting artifacts (such as images, code, and text).

Users can also review the “inner monologue” of team as they address tasks, and view profiling information such as costs associated with the run (such as number of turns, number of tokens etc.), and agent actions (such as whether tools were called and the outcomes of code execution).

## Importing and Reusing Team Configurations

AutoGen Studio provides a Gallery view which provides a built-in default gallery. A Gallery is simply is a collection of components - teams, agents, models tools etc. Furthermore, users can import components from 3rd party community sources either by providing a URL to a JSON Gallery spec or pasting in the gallery JSON. This allows users to reuse and share team configurations with others.

- Gallery -> New Gallery -> Import
- Set as default gallery (in side bar, by clicking pin icon)
- Reuse components in Team Builder. Team Builder -> Sidebar -> From Gallery

### Using AutoGen Studio Teams in a Python Application

An exported team can be easily integrated into any Python application using the `TeamManager` class with just two lines of code. Underneath, the `TeamManager` rehydrates the team specification into AutoGen AgentChat agents that are subsequently used to address tasks.

```python

from autogenstudio.teammanager import TeamManager

tm = TeamManager()
result_stream =  tm.run(task="What is the weather in New York?", team_config="team.json") # or wm.run_stream(..)

```

To export a team configuration, click on the export button in the Team Builder interface. This will generate a JSON file that can be used to rehydrate the team in a Python application.

<!-- ### Deploying AutoGen Studio Teams as APIs

The team can be launched as an API endpoint from the command line using the autogenstudio commandline tool.

```bash
autogenstudio serve --team=team.json --port=5000
```

Similarly, the team launch command above can be wrapped into a Dockerfile that can be deployed on cloud services like Azure Container Apps or Azure Web Apps. -->
