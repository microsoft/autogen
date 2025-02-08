---
myst:
  html_meta:
    "description lang=en": |
      User Guide for AutoGen Studio - A low code tool for building and debugging multi-agent systems
---

# AutoGen Studio

[![PyPI version](https://badge.fury.io/py/autogenstudio.svg)](https://badge.fury.io/py/autogenstudio)
[![Downloads](https://static.pepy.tech/badge/autogenstudio/week)](https://pepy.tech/project/autogenstudio)

AutoGen Studio is a low-code interface built to help you rapidly prototype AI agents, enhance them with tools, compose them into teams and interact with them to accomplish tasks. It is built on [AutoGen AgentChat](https://microsoft.github.io/autogen) - a high-level API for building multi-agent applications.

> See a video tutorial on AutoGen Studio v0.4 (02/25) - [https://youtu.be/oum6EI7wohM](https://youtu.be/oum6EI7wohM)

[![A Friendly Introduction to AutoGen Studio v0.4](https://img.youtube.com/vi/oum6EI7wohM/maxresdefault.jpg)](https://www.youtube.com/watch?v=oum6EI7wohM)

Code for AutoGen Studio is on GitHub at [microsoft/autogen](https://github.com/microsoft/autogen/tree/main/python/packages/autogen-studio)

```{caution}
AutoGen Studio is meant to help you rapidly prototype multi-agent workflows and demonstrate an example of end user interfaces built with AutoGen. It is not meant to be a production-ready app. Developers are encouraged to use the AutoGen framework to build their own applications, implementing authentication, security and other features required for deployed applications.
```

## Capabilities - What Can You Do with AutoGen Studio?

AutoGen Studio offers four main interfaces to help you build and manage multi-agent systems:

1. **Team Builder**

   - A visual interface for creating agent teams through declarative specification (JSON) or drag-and-drop
   - Supports configuration of all core components: teams, agents, tools, models, and termination conditions
   - Fully compatible with AgentChat's component definitions

2. **Playground**

   - Interactive environment for testing and running agent teams
   - Features include:
     - Live message streaming between agents
     - Visual representation of message flow through a control transition graph
     - Interactive sessions with teams using UserProxyAgent
     - Full run control with the ability to pause or stop execution

3. **Gallery**

   - Central hub for discovering and importing community-created components
   - Enables easy integration of third-party components

4. **Deployment**
   - Export and run teams in python code
   - Setup and test endpoints based on a team configuration
   - Run teams in a docker container

### Roadmap

Review project roadmap and issues [here](https://github.com/microsoft/autogen/issues/4006) .

## Contribution Guide

We welcome contributions to AutoGen Studio. We recommend the following general steps to contribute to the project:

- Review the overall AutoGen project [contribution guide](https://github.com/microsoft/autogen/blob/main/CONTRIBUTING.md)
- Please review the AutoGen Studio [roadmap](https://github.com/microsoft/autogen/issues/4006) to get a sense of the current priorities for the project. Help is appreciated especially with Studio issues tagged with `help-wanted`
- Please use the tag [`proj-studio`](https://github.com/microsoft/autogen/issues?q=is%3Aissue%20state%3Aopen%20label%3Aproj-studio) tag for any issues, questions, and PRs related to Studio
- Please initiate a discussion on the roadmap issue or a new issue to discuss your proposed contribution.
- Submit a pull request with your contribution!
- If you are modifying AutoGen Studio, it has its own devcontainer. See instructions in `.devcontainer/README.md` to use it

## A Note on Security

AutoGen Studio is a research prototype and is **not meant to be used** in a production environment. Some baseline practices are encouraged e.g., using Docker code execution environment for your agents.

However, other considerations such as rigorous tests related to jailbreaking, ensuring LLMs only have access to the right keys of data given the end user's permissions, and other security features are not implemented in AutoGen Studio.

If you are building a production application, please use the AutoGen framework and implement the necessary security features.

## Acknowledgements and Citation

AutoGen Studio is based on the [AutoGen](https://microsoft.github.io/autogen) project. It was adapted from a research prototype built in October 2023 (original credits: Victor Dibia, Gagan Bansal, Adam Fourney, Piali Choudhury, Saleema Amershi, Ahmed Awadallah, Chi Wang).

If you use AutoGen Studio in your research, please cite the following paper:

```
@inproceedings{autogenstudio,
  title={AUTOGEN STUDIO: A No-Code Developer Tool for Building and Debugging Multi-Agent Systems},
  author={Dibia, Victor and Chen, Jingya and Bansal, Gagan and Syed, Suff and Fourney, Adam and Zhu, Erkang and Wang, Chi and Amershi, Saleema},
  booktitle={Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing: System Demonstrations},
  pages={72--79},
  year={2024}
}
```

## Next Steps

To begin, follow the [installation instructions](installation.md) to install AutoGen Studio.

```{toctree}
:maxdepth: 1
:hidden:

installation
usage
faq
```
