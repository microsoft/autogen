<a name="readme-top"></a>

<div align="center">
<img src="https://microsoft.github.io/autogen/0.2/img/ag.svg" alt="AutoGen Logo" width="100">

[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40pyautogen)](https://twitter.com/pyautogen)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Company?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/105812540)
[![Discord](https://img.shields.io/badge/discord-chat-green?logo=discord)](https://aka.ms/autogen-discord)
[![Documentation](https://img.shields.io/badge/Documentation-AutoGen-blue?logo=read-the-docs)](https://microsoft.github.io/autogen/)
</div>

# AutoGen

**AutoGen** is a framework for creating multi-agent AI applications that can act autonomously or work alongside humans.

## Installation

```bash
# Install AgentChat and OpenAI client from Extensions
pip install -U "autogen-agentchat" "autogen-ext[openai]"
```

The current stable version is v0.4. If you are upgrading from AutoGen v0.2, please refer to the [Migration Guide](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/migration-guide.html) for detailed instructions on how to update your code and configurations.

### Hello World

Create an assistant agent using OpenAI's GPT-4o model.

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    agent = AssistantAgent("assistant", OpenAIChatCompletionClient(model="gpt-4o"))
    print(agent.run(task="Say 'Hello World!'"))

asyncio.run(main())
```

### Team

Create a group chat team with an assistant agent, a web surfer agent, and a user proxy agent
for web browsing tasks. You need to install [playwright](https://playwright.dev/python/docs/library).

```python
# pip install -U autogen-agentchat autogen-ext[openai,web-surfer]
# playwright install
import asyncio
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.web_surfer import MultimodalWebSurfer

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    assistant = AssistantAgent("assistant", model_client)
    web_surfer = MultimodalWebSurfer("web_surfer", model_client)
    user_proxy = UserProxyAgent("user_proxy")
    termination = TextMentionTermination("exit") # Type 'exit' to end the conversation.
    team = RoundRobinGroupChat([web_surfer, assistant, user_proxy], termination_condition=termination)
    await Console(team.run_stream(task="Find information about AutoGen and write a short summary."))

asyncio.run(main())
```

## Why Use AutoGen?

<div align="center">
  <img src="autogen-landing.jpg" alt="AutoGen Landing" width="500">
</div>

The AutoGen ecosystem provides everything you need to create AI agents, especially multi-agent workflows -- framework, developer tools, and applications.

The *framework* uses a layered and extensible design. Layers have clearly divided responsibilities and build on top of layers below. This design enables you to use the framework at different levels of abstraction, from high-level APIs to low-level components.

- [Core API](./python/packages/autogen-core/) implements message passing, event-driven agents, and local and distributed runtime for flexibility and power. It also support cross-language support for .NET and Python.
- [AgentChat API](./python/packages/autogen-agentchat/) implements a simpler but opinionated API rapid for prototyping. This API is built on top of the Core API and is closest to what users of v0.2 are familiar with and supports familiar multi-agent patterns such as two-agent chat or group chats.
- [Extensions API](./python/packages/autogen-ext/) enables first- and third-party extensions continuously expanding framework capabilities. It support specific implementation of LLM clients (e.g., OpenAI, AzureOpenAI), and capabilities such as code execution.

The ecosystem also supports two essential *developer tools*:

<div align="center">
  <img src="https://media.githubusercontent.com/media/microsoft/autogen/refs/heads/main/python/packages/autogen-studio/docs/ags_screen.png" alt="AutoGen Studio Screenshot" width="500">
</div>

- [AutoGen Studio](./python/packages/autogen-studio/) provides a no-code GUI for building multi-agent applications.
- [AutoGen Bench](./python/packages/agbench/) provides a benchmarking suite for evaluating agent performance.

You can use the AutoGen framework and developer tools to create applications for your domain. For example, [Magentic-One](./python/packages/magentic-one-cli/) is a state-of-art multi-agent team built using AgentChat API and Extensions API that can handle variety of tasks that require web browsing, code execution, and file handling.

With AutoGen you get to join and contribute to a thriving ecosystem. We host weekly office hours and talks with maintainers and community. We also have a [Discord server](https://aka.ms/autogen-discord) for real-time chat, GitHub Discussions for Q&A, and a blog for tutorials and updates.

## Where to go next?

<div align="center">

|                      | [![Python](https://img.shields.io/badge/AutoGen-Python-blue?logo=python&logoColor=white)](./python)                                                                                     | [![.NET](https://img.shields.io/badge/AutoGen-.NET-green?logo=.net&logoColor=white)](./dotnet)              | [![Studio](https://img.shields.io/badge/AutoGen-Studio-purple?logo=visual-studio&logoColor=white)](./python/packages/autogen-studio)              |
|----------------------|--------------------------------------------------------------------------------------------|-------------------|-------------------|
| Installation    | [![Installation](https://img.shields.io/badge/Install-blue)](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/installation.html) | *    | [![Install](https://img.shields.io/badge/Install-purple)](https://microsoft.github.io/autogen/dev/user-guide/autogenstudio-user-guide/installation.html)    |
| Quickstart | [![Quickstart](https://img.shields.io/badge/Quickstart-blue)](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/quickstart.html#) | *    | *    |
| Tutorial        | [![Tutorial](https://img.shields.io/badge/Tutorial-blue)](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/models.html)  | *| * |
| API Reference   | [![API](https://img.shields.io/badge/Docs-blue)](https://microsoft.github.io/autogen/dev/reference/index.html#) | *    | [![API](https://img.shields.io/badge/Docs-purple)](https://microsoft.github.io/autogen/dev/user-guide/autogenstudio-user-guide/usage.html) |
| Packages        | [![PyPi autogen-core](https://img.shields.io/badge/PyPi-autogen--core-blue?logo=pypi)](https://pypi.org/project/autogen-core/) <br> [![PyPi autogen-agentchat](https://img.shields.io/badge/PyPi-autogen--agentchat-blue?logo=pypi)](https://pypi.org/project/autogen-agentchat/) <br> [![PyPi autogen-ext](https://img.shields.io/badge/PyPi-autogen--ext-blue?logo=pypi)](https://pypi.org/project/autogen-ext/) | *    | [![PyPi autogenstudio](https://img.shields.io/badge/PyPi-autogenstudio-purple?logo=pypi)](https://pypi.org/project/autogenstudio/) |

</div>

**Releasing soon*

Interested in contributing? See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on how to get started. We welcome contributions of all kinds, including bug fixes, new features, and documentation improvements. Join our community and help us make AutoGen better!

Have questions? Check out our [Frequently Asked Questions (FAQ)](./FAQ.md) for answers to common queries. If you don't find what you're looking for, feel free to ask in our [GitHub Discussions](https://github.com/microsoft/autogen/discussions) or join our [Discord server](https://aka.ms/autogen-discord) for real-time support.

## Legal Notices

Microsoft and any contributors grant you a license to the Microsoft documentation and other content
in this repository under the [Creative Commons Attribution 4.0 International Public License](https://creativecommons.org/licenses/by/4.0/legalcode),
see the [LICENSE](LICENSE) file, and grant you a license to any code in the repository under the [MIT License](https://opensource.org/licenses/MIT), see the
[LICENSE-CODE](LICENSE-CODE) file.

Microsoft, Windows, Microsoft Azure, and/or other Microsoft products and services referenced in the documentation
may be either trademarks or registered trademarks of Microsoft in the United States and/or other countries.
The licenses for this project do not grant you rights to use any Microsoft names, logos, or trademarks.
Microsoft's general trademark guidelines can be found at <http://go.microsoft.com/fwlink/?LinkID=254653>.

Privacy information can be found at <https://go.microsoft.com/fwlink/?LinkId=521839>

Microsoft and any contributors reserve all other rights, whether under their respective copyrights, patents,
or trademarks, whether by implication, estoppel, or otherwise.

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>
