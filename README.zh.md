<a name="readme-top"></a>

<div align="center">
<img src="https://microsoft.github.io/autogen/0.2/img/ag.svg" alt="AutoGen Logo" width="100">

[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40pyautogen)](https://twitter.com/pyautogen)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Company?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/105812540)
[![Discord](https://img.shields.io/badge/discord-chat-green?logo=discord)](https://aka.ms/autogen-discord)
[![Documentation](https://img.shields.io/badge/Documentation-AutoGen-blue?logo=read-the-docs)](https://microsoft.github.io/autogen/)
[![Blog](https://img.shields.io/badge/Blog-AutoGen-blue?logo=blogger)](https://devblogs.microsoft.com/autogen/)

<p align="center">
  <a href="README.md">English</a> · <b>简体中文</b>
</p>

</div>

# AutoGen [![维护模式状态](https://img.shields.io/badge/status-maintenance%20mode-orange)](https://github.com/microsoft/agent-framework)

**AutoGen** 是一个用于创建多智能体 AI 应用的开源开发框架，智能体既可以自主执行任务，也可以与人类协同工作。

> [!CAUTION]
> **⚠️ 维护模式说明**
>
> AutoGen 目前已进入**维护模式（Maintenance Mode）**。后续将不再接收新功能与特性升级，转由社区共同维护。
>
> 新用户建议直接使用 [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)。现有用户建议参考 [AutoGen → Microsoft Agent Framework 迁移指南](https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/) 进行平滑过渡。
>
> Microsoft Agent Framework (MAF) 是 AutoGen 面向企业级场景的正式继任者，现已推出稳定生产版本：提供稳定的 API 与长期支持承诺。无论是构建单一 AI 助手，还是编排由专业智能体组成的大型协作机群，Microsoft Agent Framework 1.0 均提供了企业级多智能体编排调度、多模型供应商支持，以及通过 A2A 和 MCP 协议实现的跨运行时互操作性。

## 安装指南

AutoGen 需要 **Python 3.10 或更高版本**。

```bash
# 安装 AgentChat 核心库以及 OpenAI 扩展客户端
pip install -U "autogen-agentchat" "autogen-ext[openai]"
```

当前稳定版本可查阅 [GitHub Releases](https://github.com/microsoft/autogen/releases)。如果您正在从 AutoGen v0.2 进行升级，请参阅[迁移指南](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/migration-guide.html)获取有关更新代码和配置的详细说明。

```bash
# 安装无代码可视化界面 AutoGen Studio
pip install -U "autogenstudio"
```

## 快速入门

以下示例将调用 OpenAI API，因此需要先配置 API Key：`export OPENAI_API_KEY="sk-..."`。

### 1. Hello World 基础助手

使用 OpenAI 的 GPT-4o 模型创建最基础的助手智能体（查阅[其他支持的模型列表](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/models.html)）：

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1")
    agent = AssistantAgent("assistant", model_client=model_client)
    print(await agent.run(task="Say 'Hello World!'"))
    await model_client.close()

asyncio.run(main())
```

### 2. 集成 MCP Server 工具服务器

创建一个使用 Playwright MCP 服务进行网页浏览与信息检索的智能体：

```python
# 首先执行 `npm install -g @playwright/mcp@latest` 安装 MCP 服务器
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams


async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1")
    server_params = StdioServerParams(
        command="npx",
        args=[
            "@playwright/mcp@latest",
            "--headless",
        ],
    )
    async with McpWorkbench(server_params) as mcp:
        agent = AssistantAgent(
            "web_browsing_assistant",
            model_client=model_client,
            workbench=mcp, # 若连接多个 MCP 服务器，可传入列表
            model_client_stream=True,
            max_tool_iterations=10,
        )
        await Console(agent.run_stream(task="Find out how many contributors for the microsoft/autogen repository"))


asyncio.run(main())
```

> **安全警告**：请仅连接受信任的 MCP 服务器，因为外部服务器可能在您的本地环境中执行系统命令或暴露敏感信息。

### 3. 多智能体编排协同 (Multi-Agent Orchestration)

使用 `AgentTool` 将专业智能体封装为工具，实现基础的多智能体分工协作模式：

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.tools import AgentTool
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1")

    # 1. 数学专家智能体
    math_agent = AssistantAgent(
        "math_expert",
        model_client=model_client,
        system_message="You are a math expert.",
        description="A math expert assistant.",
        model_client_stream=True,
    )
    math_agent_tool = AgentTool(math_agent, return_value_as_last_message=True)

    # 2. 化学专家智能体
    chemistry_agent = AssistantAgent(
        "chemistry_expert",
        model_client=model_client,
        system_message="You are a chemistry expert.",
        description="A chemistry expert assistant.",
        model_client_stream=True,
    )
    chemistry_agent_tool = AgentTool(chemistry_agent, return_value_as_last_message=True)

    # 3. 总体协调总管智能体
    agent = AssistantAgent(
        "assistant",
        system_message="You are a general assistant. Use expert tools when needed.",
        model_client=model_client,
        model_client_stream=True,
        tools=[math_agent_tool, chemistry_agent_tool],
        max_tool_iterations=10,
    )
    await Console(agent.run_stream(task="What is the integral of x^2?"))
    await Console(agent.run_stream(task="What is the molecular weight of water?"))


asyncio.run(main())
```

更多进阶的多智能体编排与工作流模式，请阅读 [AgentChat 官方文档](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html)。

### 4. AutoGen Studio 可视化工作台

无需编写代码即可快速原型设计与运行多智能体工作流：

> **注意**：AutoGen Studio 主要用于帮助开发者快速验证多智能体工作流概念并作为 UI 范例。**它并非生产就绪型应用**。建议开发者使用 AutoGen 框架构建自己的定制化前端，实现完善的认证与安全机制。详情参阅[安全说明文档](https://microsoft.github.io/autogen/dev/user-guide/autogenstudio-user-guide/index.html#a-note-on-security)。

```bash
# 在本地 8080 端口启动 AutoGen Studio
autogenstudio ui --port 8080 --appdir ./my-app
```

## 为什么选择 AutoGen？

<div align="center">
  <img src="autogen-landing.jpg" alt="AutoGen 架构概览" width="500">
</div>

由微软研究院（Microsoft Research）开创的 AutoGen 率先提出了实验性多智能体编排范式，启发了整个开源社区。虽然 AutoGen 目前已转入维护模式，但现有用户仍可基于以下分层架构继续开发与使用。**对于全新项目，推荐使用 [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)**。

AutoGen 框架采用**模块化分层与可扩展架构**设计，各层职责清晰分明：

- [Core API](./python/packages/autogen-core/)：实现异步消息传递、事件驱动智能体，以及支持灵活强大的本地和分布式运行时，原生支持 .NET 与 Python 跨语言互操作。
- [AgentChat API](./python/packages/autogen-agentchat/)：基于 Core API 构建的高级交互接口，支持双智能体对话、群体讨论等常见多智能体协作模式。
- [Extensions API](./python/packages/autogen-ext/)：提供丰富的官方与第三方插件扩展，覆盖各类 LLM 客户端（OpenAI、AzureOpenAI 等）与安全代码执行环境。

生态体系同时包含两款关键的**开发者工具**：

<div align="center">
  <img src="https://media.githubusercontent.com/media/microsoft/autogen/refs/heads/main/python/packages/autogen-studio/docs/ags_screen.png" alt="AutoGen Studio 界面截图" width="500">
</div>

- [AutoGen Studio](./python/packages/autogen-studio/)：构建与测试多智能体应用的无代码 GUI 界面。
- [AutoGen Bench](./python/packages/agbench/)：评估与衡量智能体任务完成能力的基准测试套件。

例如，[Magentic-One](./python/packages/magentic-one-cli/) 是由微软基于 AgentChat 与 Extensions API 打造的多智能体系统，可全自动处理需要复杂网页浏览、代码编写运行与文件读写的综合任务。

社区支持请访问 [Discord 社区](https://aka.ms/autogen-discord) 或 [GitHub Discussions](https://github.com/microsoft/autogen/discussions)。由于 AutoGen 目前由社区接管维护，响应时间可能存在延迟。

## 资源导航与进阶指引

> **开启新项目？** 前往 [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) 探索最新企业级多智能体能力。
>
> **现有 AutoGen 用户？** 参阅[迁移指南](https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/)平滑过渡，或参考下方资源查阅 AutoGen 文档。

<div align="center">

|               | [![Python](https://img.shields.io/badge/AutoGen-Python-blue?logo=python&logoColor=white)](./python)                                                                                                                                                                                                                                                                                                                | [![.NET](https://img.shields.io/badge/AutoGen-.NET-green?logo=.net&logoColor=white)](./dotnet)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | [![Studio](https://img.shields.io/badge/AutoGen-Studio-purple?logo=visual-studio&logoColor=white)](./python/packages/autogen-studio)                        |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 安装指南 (Install)  | [![Installation](https://img.shields.io/badge/Install-blue)](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/installation.html)                                                                                                                                                                                                                                                         | [![Install](https://img.shields.io/badge/Install-green)](https://microsoft.github.io/autogen/dotnet/dev/core/installation.html)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | [![Install](https://img.shields.io/badge/Install-purple)](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/installation.html) |
| 快速入门 (Quickstart)    | [![Quickstart](https://img.shields.io/badge/Quickstart-blue)](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/quickstart.html#)                                                                                                                                                                                                                                                         | [![Quickstart](https://img.shields.io/badge/Quickstart-green)](https://microsoft.github.io/autogen/dotnet/dev/core/index.html)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | [![Usage](https://img.shields.io/badge/Quickstart-purple)](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/usage.html#)      |
| 教程教程 (Tutorial)      | [![Tutorial](https://img.shields.io/badge/Tutorial-blue)](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/index.html)                                                                                                                                                                                                                                                          | [![Tutorial](https://img.shields.io/badge/Tutorial-green)](https://microsoft.github.io/autogen/dotnet/dev/core/tutorial.html)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | [![Usage](https://img.shields.io/badge/Tutorial-purple)](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/usage.html#)        |
| API 参考 (API Reference) | [![API](https://img.shields.io/badge/Docs-blue)](https://microsoft.github.io/autogen/stable/reference/index.html#)                                                                                                                                                                                                                                                                                                 | [![API](https://img.shields.io/badge/Docs-green)](https://microsoft.github.io/autogen/dotnet/dev/api/Microsoft.AutoGen.Contracts.html)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | [![API](https://img.shields.io/badge/Docs-purple)](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/usage.html)               |
| 安装包 (Packages)      | [![PyPi autogen-core](https://img.shields.io/badge/PyPi-autogen--core-blue?logo=pypi)](https://pypi.org/project/autogen-core/) <br> [![PyPi autogen-agentchat](https://img.shields.io/badge/PyPi-autogen--agentchat-blue?logo=pypi)](https://pypi.org/project/autogen-agentchat/) <br> [![PyPi autogen-ext](https://img.shields.io/badge/PyPi-autogen--ext-blue?logo=pypi)](https://pypi.org/project/autogen-ext/) | [![NuGet Contracts](https://img.shields.io/badge/NuGet-Contracts-green?logo=nuget)](https://www.nuget.org/packages/Microsoft.AutoGen.Contracts/) <br> [![NuGet Core](https://img.shields.io/badge/NuGet-Core-green?logo=nuget)](https://www.nuget.org/packages/Microsoft.AutoGen.Core/) <br> [![NuGet Core.Grpc](https://img.shields.io/badge/NuGet-Core.Grpc-green?logo=nuget)](https://www.nuget.org/packages/Microsoft.AutoGen.Core.Grpc/) <br> [![NuGet RuntimeGateway.Grpc](https://img.shields.io/badge/NuGet-RuntimeGateway.Grpc-green?logo=nuget)](https://www.nuget.org/packages/Microsoft.AutoGen.RuntimeGateway.Grpc/) | [![PyPi autogenstudio](https://img.shields.io/badge/PyPi-autogenstudio-purple?logo=pypi)](https://pypi.org/project/autogenstudio/)                          |

</div>

有意参与贡献？请参阅 [贡献指南 (CONTRIBUTING.md)](./CONTRIBUTING.md)。由于 AutoGen 处于维护模式，贡献主要限于 Bug 修复、安全补丁与文档改进。如需进行新特性开发，欢迎参与 [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) 贡献。

常见问题请查阅 [常见问题解答 (FAQ.md)](./FAQ.md)。

## 法律声明与开源许可

微软与贡献者根据 [知识共享署名 4.0 国际许可协议 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/legalcode) 授予您使用本仓库中 Microsoft 文档和其他内容的权利，请参阅 [LICENSE](LICENSE) 文件；并根据 [MIT 许可证](https://opensource.org/licenses/MIT) 授予您使用本仓库中所有代码的权利，请参阅 [LICENSE-CODE](LICENSE-CODE) 文件。

文档中提及的 Microsoft、Windows、Microsoft Azure 和/或其他微软产品与服务可能是微软在美国和/或其他国家/地区的商标或注册商标。本项目许可证并未授予您使用任何微软名称、商标或标识的权利。微软通用商标使用准则请查阅 <http://go.microsoft.com/fwlink/?LinkID=254653>。

隐私声明请查阅 <https://go.microsoft.com/fwlink/?LinkId=521839>。

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

---

> 💡 **文档维护说明**：本中文文档由社区志愿者（@JasonYeYuhe）翻译维护，最后同步更新于 2026年8月31日。如发现内容与官方英文原版存在差异或新特性滞后，欢迎提交 PR 共同完善！
