<a name="readme-top"></a>

<div align="center">
<img src="https://microsoft.github.io/autogen/img/ag.svg" alt="AutoGen Logo" width="100">

[![PyPI version](https://badge.fury.io/py/autogen-agentchat.svg)](https://badge.fury.io/py/autogen-agentchat)
[![NuGet version](https://badge.fury.io/nu/AutoGen.Core.svg)](https://badge.fury.io/nu/AutoGen.Core)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40pyautogen)](https://twitter.com/pyautogen)

</div>

# AutoGen

AutoGen is an open-source framework for building AI agent systems.
It simplifies the creation of event-driven, distributed, scalable, and resilient AI applications.
Using AutoGen, you can quickly build systems where AI agents collaborate
and perform tasks autonomously or with human oversight.

* [Installation](#install)
* [Quickstart](#quickstart)
* [Using AutoGen](#using-autogen)
* [Roadmap](#roadmap)
* [FAQs](#faqs)

AutoGen streamlines AI development and research, enabling the use of multiple large language models (LLMs), integrated tools, and advanced multi-agent design patterns.
You can develop and test your agent systems locally, then seamlessly deploy to a distributed cloud environment as your needs grow.

:fire: **September 18, 2024**: AutoGen 0.5 is a new architecture for AutoGen! This new version is in preview release and being developed in the open over the next several weeks as we refine the documentation, samples, and work with our users on evolving this new version. 🚀

- AutoGen 0.5 represents a rearchitecutre of the system to make it more scalable, resilient, and interoperable across multiple programming languages.
- It is designed to be more modular and extensible, with a focus on enabling a wide range of applications and use cases.
- This redesign features full .NET and Python libraries, with more languages to come.  Agents may be written in different languages and interoperate with one another over a common messaging protocol using the CloudEvents standard.

## Install

### Python

AutoGen requires Python 3.10+. It has multiple packages.

```bash
pip install autogen-agentchat autogen-core autogen-ext
```

See [packages](https://microsoft.github.io/agnext/packages) for more information about available packages.

### .NET

(Add .NET installation instruction here)

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Quickstart

### Python

```python
import asyncio
import os
from autogen_core.components.models import chat_completion_client_from_json as client_from_json
from autogen_agentchat import CodingAssistant, CodeExecutorAgent, RoundRobinTeam, console_output
from autogen_ext.code_executors import DockerCommandLineCodeExecutor

async def main():
    chat_completion_client = client_from_json(os.environ["MODEL_CLIENT_JSON"])
    async with DockerCommandLineCodeExecutor(work_dir="coding") as executor:
        assistant = CodingAssistant("assistant", chat_completion_client=chat_completion_client)
        executor_agent = CodeExecutorAgent(
            "code_executor", executor=executor,
        )
        team = RoundRobinTeam(agents=[assistant, executor_agent])
        result = await team.run("Plot a chart of NVDA and TESLA stock price change YTD. Save the plot to a file called plot.png", output=console_output)

if __name__ == "__main__":
    asyncio.run(main())
```

### C#

(Add .NET quickstart here)

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Using AutoGen

The version you are looking at is AutoGen 0.5, which introduces a new architecture.
The best place to start is the [documentation](https://microsoft.github.io/agnext).

The new architecture provides the following features:

- **Asynchronous Messaging**: Agents communicate via asynchronous messages, supporting both event-driven and request/response interaction patterns.
- **Scalable & Distributed**: Design complex, distributed agent networks that can operate across organizational boundaries.
- **Modular & Extensible**: Customize your system with pluggable components, including custom agents, memory services, tool registries, and model libraries.
- **Cross-Language Support**: Interoperate agents across different programming languages. Currently supports Python and .NET, with more languages coming soon.
- **Observability & Debugging**: Built-in tools for tracking, tracing, and debugging agent interactions and workflows.

We are actively developing this new architecture, but we are excited to share our progress with you.
We are looking for your feedbacks and contributions to help shape the future of AutoGen.

The current stable release is AutoGen 0.2.
You can find the documentation [here](https://microsoft.github.io/autogen).

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Roadmap

- [AutoGen 0.2] - This is the current stable release of AutoGen. We will continue to accept bug fixes and minor enhancements to this version.
- [AutoGen 0.5] - This is the first release of the new event-driven architecture. This release is still in preview.  We will be focusing on stability of the interfaces, documentation, tutorials, samples, and a collection of base agents from which you can inherit. We are also working on compatibility interfaces for those familiar with prior versions of AutoGen.
- [future] - We are excited to work with our community to define the future of AutoGen. We are looking for feedback and contributions to help shape the future of this project.Here are some major planned items:
  - [ ] Add support for more languages
  - [ ] Add support for more base agents and patterns
  - [ ] Add compatibility with Bot Framework Activity Protocol

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## FAQs

Q: What is AutoGen 0.5?

AutoGen 0.5 is a rewrite of AutoGen from the ground up to create a more robust, scalable, easier to use, cross-language library for building AI Agents.

Q: Why these changes?

We listened to our AutoGen users, learned from what was working, and adapted to fix what wasn't. We brought together wide ranging teams working on many different types of AI Agents and collaborated to design an improved framework with a more flexible programming model and better scalability.

Q: Who should use it?

This code is still experimental. We encourage adventurous early adopters to please try it out, give us feedback, and contribute.

Q: I'm using AutoGen 0.2, should I upgrade?

If you consider yourself an early adopter, you are comfortable making some changes to your code, and are willing to try it out, then yes.

Q:  How do I still use AutoGen 0.2?

Just keep doing what you were doing before.

Q: How do I migrate?

We are working on a migration guide. Until then, see the [documentation](http://microsoft.github.io/agnext).

Q: What is happening next? When will this release be ready?

We are still working on improving the documentation, samples, and enhancing the code. We will prepare a release announcement when these things are completed in the next few weeks.

Q: What is the history of this project?

The rearchitecture of AutoGen came from multiple Microsoft teams coming together to build the next generation of AI agent framework - merging ideas from several predecessor projects.
The team decided to bring this work to OSS as an evolution of AutoGen in September 2024.
Prior to that, AutoGen has been developed and maintained by [a community of contributors](CONTRIBUTORS.md).

Q: What is the official channel for support?

Use GitHub [Issues](https://github.com/microsoft/agnext/issues) for bug reports and feature requests.
Use GitHub [Discussions](https://github.com/microsoft/agnext/discussions) for general questions and discussions.

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Legal Notices

Microsoft and any contributors grant you a license to the Microsoft documentation and other content
in this repository under the [Creative Commons Attribution 4.0 International Public License](https://creativecommons.org/licenses/by/4.0/legalcode),
see the [LICENSE](LICENSE) file, and grant you a license to any code in the repository under the [MIT License](https://opensource.org/licenses/MIT), see the
[LICENSE-CODE](LICENSE-CODE) file.

Microsoft, Windows, Microsoft Azure, and/or other Microsoft products and services referenced in the documentation
may be either trademarks or registered trademarks of Microsoft in the United States and/or other countries.
The licenses for this project do not grant you rights to use any Microsoft names, logos, or trademarks.
Microsoft's general trademark guidelines can be found at http://go.microsoft.com/fwlink/?LinkID=254653.

Privacy information can be found at https://go.microsoft.com/fwlink/?LinkId=521839

Microsoft and any contributors reserve all other rights, whether under their respective copyrights, patents,
or trademarks, whether by implication, estoppel, or otherwise.

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>