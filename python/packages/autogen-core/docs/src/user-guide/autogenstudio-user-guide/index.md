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

![AutoGen Studio](https://media.githubusercontent.com/media/microsoft/autogen/refs/heads/main/python/packages/autogen-studio/docs/ags_screen.png)

Code for AutoGen Studio is on GitHub at [microsoft/autogen](https://github.com/microsoft/autogen/tree/main/python/packages/autogen-studio)

> **Note**: AutoGen Studio is meant to help you rapidly prototype multi-agent workflows and demonstrate an example of end user interfaces built with AutoGen. It is not meant to be a production-ready app. Developers are encouraged to use the AutoGen framework to build their own applications, implementing authentication, security and other features required for deployed applications.

## Capabilities

AutoGen Studio provides the following capabilities:

- A **Team Builder** view interface that supports the declarative specification (or drag and drop componsition) of components - teams, agents, tools, models, termination conditions as defined in AgentChat.
- A **PlayGround** view where users can define sessions (each session is assigned a team) and run tasks interactively.
  - Realtime stream of messages as agents act
  - Control flow transition graph of messages sent by agents
  - Human in the loop support for teams that include a UserProxyAgent, allowing users to interact with the team run in real time.
  - Run control: ability to intervene and stop a run mid-execution.
- A **Gallery view** where users can import components from 3rd party community sources.
- A **Deployment view** interface where users can explore deployment options for teams.

### Roadmap

Review project roadmap and issues [here](https://github.com/microsoft/autogen/issues/4006) .

Project Structure:

- _autogenstudio/_ code for the backend classes and web api (FastAPI)
- _frontend/_ code for the webui, built with Gatsby and TailwindCSS

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
