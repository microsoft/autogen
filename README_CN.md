<a name="readme-top"></a>

<div align="center">

<img src="https://microsoft.github.io/autogen/img/ag.svg" alt="AutoGen Logo" width="100">

![Python Version](https://img.shields.io/badge/3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue) [![PyPI - Version](https://img.shields.io/pypi/v/autogen-agentchat)](https://pypi.org/project/autogen-agentchat/)
[![NuGet version](https://badge.fury.io/nu/AutoGen.Core.svg)](https://badge.fury.io/nu/AutoGen.Core)

[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40pyautogen)](https://twitter.com/pyautogen)

</div>

# AutoGen

AutoGen 是一个开源编程框架，用于构建 AI 代理并促进多个代理之间的合作来解决任务。AutoGen 旨在简化代理 AI 的开发和研究，就像 PyTorch 对深度学习的作用一样。它提供了多种功能，如能够相互交互的代理，支持各种大型语言模型（LLM）的使用和工具支持，自动化和人工参与的工作流程，以及多代理的对话模式。

> [!重要]
> 为了更好地适应即将推出的新多包结构，自版本 `0.2.36` 起，AutoGen 现在可以通过 PyPi 的 [`autogen-agentchat`](https://pypi.org/project/autogen-agentchat/) 获取。这是 AutoGen 项目的官方包。

> [!注意]
> *贡献者和用户须知*：</b> [microsoft/autogen](https://aka.ms/autogen-gh) 是 AutoGen 项目的原始仓库，它正在 MIT 许可证下积极开发和维护。我们欢迎来自全球开发者和组织的贡献。我们的目标是促进一个协作和包容的社区，通过多样化的视角和专业知识推动创新并增强项目的能力。我们感谢现有贡献者的宝贵贡献，详见 [contributors.md](./CONTRIBUTORS.md)。无论您是个人贡献者还是代表组织，我们邀请您加入我们，共同塑造该项目的未来。更多信息请参阅 [Microsoft 开源贡献指南](https://github.com/microsoft/autogen?tab=readme-ov-file#contributing)。
>
> -_维护者 (2024年9月6日)_

![AutoGen 概述](https://github.com/microsoft/autogen/blob/main/website/static/img/autogen_agentchat.png)

- AutoGen 使基于[多代理对话](https://microsoft.github.io/autogen/docs/Use-Cases/agent_chat)构建下一代 LLM 应用程序变得更加轻松。它简化了复杂 LLM 工作流程的编排、自动化和优化，最大限度地提高了 LLM 模型的性能，并克服了其弱点。
- 它支持用于复杂工作流程的[多样化对话模式](https://microsoft.github.io/autogen/docs/Use-Cases/agent_chat#supporting-diverse-conversation-patterns)。通过可自定义和可对话的代理，开发人员可以使用 AutoGen 构建多种关于对话自主性、代理数量和代理对话拓扑的对话模式。
- 它提供了一系列具有不同复杂性的工作系统。这些系统跨越了[广泛的应用领域](https://microsoft.github.io/autogen/docs/Use-Cases/agent_chat#diverse-applications-implemented-with-autogen)，展示了 AutoGen 如何轻松支持多样化的对话模式。
- AutoGen 提供了[增强的 LLM 推理](https://microsoft.github.io/autogen/docs/Use-Cases/enhanced_inference#api-unification)，包括 API 统一和缓存等工具，及高级使用模式，如错误处理、多配置推理、上下文编程等。

AutoGen 是由 Microsoft、宾夕法尼亚州立大学和华盛顿大学的[合作研究](https://microsoft.github.io/autogen/docs/Research)创建的。

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

## 新闻
<details>

<summary>展开</summary>

## 路线图

要了解我们正在进行的工作和未来的计划，请查看我们的
[路线图问题](https://aka.ms/autogen-roadmap)。

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

## 快速开始

最简单的开始方法是：
1. 点击下方链接，使用 GitHub Codespace

    [![在 GitHub Codespaces 中打开](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/autogen?quickstart=1)

2. 将 OAI_CONFIG_LIST_sample 复制到 ./notebook 文件夹中，重命名为 OAI_CONFIG_LIST，并设置正确的配置。
3. 开始使用这些 notebooks 进行操作！

*注意*：OAI_CONFIG_LIST_sample 将 GPT-4 设置为默认模型，因为这是我们当前推荐的模型，并且已知与 AutoGen 兼容良好。如果您使用除 GPT-4 以外的模型，可能需要修改系统提示（尤其是使用较弱模型如 GPT-3.5-turbo 时）。此外，若您使用 OpenAI 或 Azure 以外的模型，可能会增加与对齐和安全相关的风险。如果更新默认模型，请谨慎操作。

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

## [安装](https://microsoft.github.io/autogen/docs/Installation)

### 选项1. 在 Docker 中安装并运行 AutoGen

用户可以在 [这里](https://microsoft.github.io/autogen/docs/installation/Docker#step-1-install-docker) 找到详细的安装说明，开发者可以在 [这里](https://microsoft.github.io/autogen/docs/Contribute#docker-for-development) 找到相关说明。

### 选项2. 本地安装 AutoGen

AutoGen 需要 **Python 版本 >= 3.8, < 3.13**。可以通过 pip 安装：

```bash
pip install autogen-agentchat~=0.2
```

最小依赖项会在没有额外选项的情况下安装。您可以根据需要的功能安装额外选项。

<!-- 例如，使用以下命令安装 [`blendsearch`](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function#blendsearch-economical-hyperparameter-optimization-with-blended-search-strategy) 所需的依赖项。
```bash
pip install "autogen-agentchat[blendsearch]~=0.2"
``` -->

在 [安装说明](https://microsoft.github.io/autogen/docs/Installation#option-2-install-autogen-locally-using-virtual-environment) 中找到更多选项。

<!-- 每个 [`notebook 示例`](https://github.com/microsoft/autogen/tree/main/notebook) 可能需要安装特定的选项。 -->

即使您在本地安装和运行 AutoGen，而不是在 Docker 中运行，推荐的代理默认行为是使用 [代码执行](https://microsoft.github.io/autogen/docs/FAQ/#code-execution) 在 Docker 中执行。请在 [这里](https://microsoft.github.io/autogen/docs/Installation#code-execution-with-docker-(default)) 找到更多说明以及如何更改默认行为。

有关 LLM 推理配置，请查看 [常见问题](https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints)。

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

## 多代理对话框架

AutoGen 通过通用的 [多代理对话](https://microsoft.github.io/autogen/docs/Use-Cases/agent_chat) 框架，推动下一代 LLM 应用程序的开发。它提供可定制且支持对话的代理，能够集成 LLM、工具和人类参与。
通过自动化多个智能代理之间的对话，可以轻松地让它们集体自主或通过人类反馈执行任务，包括需要通过代码使用工具的任务。

此用例的功能包括：

- **多代理对话**：AutoGen 代理可以相互通信来解决任务。这允许比单个 LLM 更复杂和高级的应用。
- **定制化**：AutoGen 代理可以根据应用程序的具体需求进行定制，包括选择使用的 LLM、允许的人类输入类型以及使用的工具。
- **人类参与**：AutoGen 无缝支持人类参与，这意味着在需要时，人类可以向代理提供输入和反馈。

例如，

```python
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
# 从环境变量或文件加载 LLM 推理端点
# 请参阅 https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
# 和 OAI_CONFIG_LIST_sample
config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
# 您也可以直接将 config_list 设置为一个列表，例如 config_list = [{'model': 'gpt-4', 'api_key': '<你的 OpenAI API 密钥>'},]
assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
user_proxy = UserProxyAgent("user_proxy", code_execution_config={"work_dir": "coding", "use_docker": False}) # 重要：设置为 True 以在 Docker 中运行代码，推荐设置
user_proxy.initiate_chat(assistant, message="绘制 NVDA 和 TESLA 年初至今股票价格变动的图表。")
# 这将启动两个代理之间的自动对话来解决任务

此示例可以通过以下命令运行

```python
python test/twoagent.py
```
在克隆仓库后。
下图显示了 AutoGen 的一个对话流示例。
![代理对话示例](https://github.com/microsoft/autogen/blob/main/website/static/img/chat_example.png)

另外，[此示例代码](https://github.com/microsoft/autogen/blob/main/samples/simple_chat.py) 允许用户以 ChatGPT 风格与 AutoGen 代理聊天。
请查找更多 [代码示例](https://microsoft.github.io/autogen/docs/Examples#automated-multi-agent-chat) 以获取此功能。

## 增强的 LLM 推理

Autogen 还帮助最大化利用昂贵的 LLM，如 ChatGPT 和 GPT-4。它提供了 [增强的 LLM 推理](https://microsoft.github.io/autogen/docs/Use-Cases/enhanced_inference#api-unification)，具有强大的功能，如缓存、错误处理、多配置推理和模板化。

<!-- 例如，您可以通过自己的调优数据、成功指标和预算来优化 LLM 的生成。

```python
# perform tuning for openai<1
config, analysis = autogen.Completion.tune(
    data=tune_data,
    metric="success",
    mode="max",
    eval_func=eval_func,
    inference_budget=0.05,
    optimization_budget=3,
    num_samples=-1,
)
# perform inference for a test instance
response = autogen.Completion.create(context=test_instance, **config)
```

请查找更多 [代码示例](https://microsoft.github.io/autogen/docs/Examples#tune-gpt-models) 以获取此功能。 -->

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

## 文档

您可以在 [这里](https://microsoft.github.io/autogen/) 找到有关 AutoGen 的详细文档。

此外，您可以找到：

- 关于 AutoGen 的 [研究](https://microsoft.github.io/autogen/docs/Research)、[博客文章](https://microsoft.github.io/autogen/blog) 和 [透明度常见问题](https://github.com/microsoft/autogen/blob/main/TRANSPARENCY_FAQS.md)

- [贡献指南](https://microsoft.github.io/autogen/docs/Contribute)

- [路线图](https://github.com/orgs/microsoft/projects/989/views/3)

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

## 相关论文

[AutoGen Studio](https://www.microsoft.com/en-us/research/publication/autogen-studio-a-no-code-developer-tool-for-building-and-debugging-multi-agent-systems/)

```
@inproceedings{dibia2024studio,
      title={AutoGen Studio: A No-Code Developer Tool for Building and Debugging Multi-Agent Systems},
      author={Victor Dibia and Jingya Chen and Gagan Bansal and Suff Syed and Adam Fourney and Erkang (Eric) Zhu and Chi Wang and Saleema Amershi},
      year={2024},
      booktitle={Pre-Print}
}
```
[AutoGen](https://aka.ms/autogen-pdf)

```
@inproceedings{wu2023autogen,
      title={AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework},
      author={Qingyun Wu and Gagan Bansal and Jieyu Zhang and Yiran Wu and Beibin Li and Erkang Zhu and Li Jiang and Xiaoyun Zhang and Shaokun Zhang and Jiale Liu and Ahmed Hassan Awadallah and Ryen W White and Doug Burger and Chi Wang},
      year={2024},
      booktitle={COLM},
}
```

[EcoOptiGen](https://arxiv.org/abs/2303.04673)

```
@inproceedings{wang2023EcoOptiGen,
    title={Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference},
    author={Chi Wang and Susan Xueqing Liu and Ahmed H. Awadallah},
    year={2023},
    booktitle={AutoML'23},
}
```

[MathChat](https://arxiv.org/abs/2306.01337)

```
@inproceedings{wu2023empirical,
    title={An Empirical Study on Challenging Math Problem Solving with GPT-4},
    author={Yiran Wu and Feiran Jia and Shaokun Zhang and Hangyu Li and Erkang Zhu and Yue Wang and Yin Tat Lee and Richard Peng and Qingyun Wu and Chi Wang},
    year={2023},
    booktitle={ArXiv preprint arXiv:2306.01337},
}
```

[AgentOptimizer](https://arxiv.org/pdf/2402.11359)

```
@article{zhang2024training,
  title={Training Language Model Agents without Modifying Language Models},
  author={Zhang, Shaokun and Zhang, Jieyu and Liu, Jiale and Song, Linxin and Wang, Chi and Krishna, Ranjay and Wu, Qingyun},
  journal={ICML'24},
  year={2024}
}
```

[StateFlow](https://arxiv.org/abs/2403.11322)
```
@article{wu2024stateflow,
  title={StateFlow: Enhancing LLM Task-Solving through State-Driven Workflows},
  author={Wu, Yiran and Yue, Tianwei and Zhang, Shaokun and Wang, Chi and Wu, Qingyun},
  journal={arXiv preprint arXiv:2403.11322},
  year={2024}
}
```

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

## 贡献

本项目欢迎贡献和建议。大多数贡献要求您同意贡献者许可协议（CLA），声明您有权利并且确实授予我们使用您贡献的权利。有关详细信息，请访问 <https://cla.opensource.microsoft.com>。

如果您是 GitHub 新手，您可以查看 [这里](https://opensource.guide/how-to-contribute/#how-to-submit-a-contribution) 获取有关如何参与 GitHub 开发的详细帮助资源。

当您提交拉取请求时，CLA 机器人会自动确定您是否需要提供 CLA，并适当地装饰 PR（例如，状态检查、评论）。只需按照机器人提供的说明进行操作。您只需在所有使用我们 CLA 的仓库中执行此操作一次。

本项目采用了 [微软开源行为准则](https://opensource.microsoft.com/codeofconduct/)。有关更多信息，请参见 [行为准则常见问题解答](https://opensource.microsoft.com/codeofconduct/faq/) 或联系 [opencode@microsoft.com](mailto:opencode@microsoft.com)，以获取任何其他问题或评论。

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

## 贡献者墙
<a href="https://github.com/microsoft/autogen/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=microsoft/autogen&max=204" />
</a>

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>

# 法律声明

微软及任何贡献者授予您使用本仓库中的微软文档和其他内容的许可，依据 [创意共享署名 4.0 国际公共许可证](https://creativecommons.org/licenses/by/4.0/legalcode)，请参阅 [LICENSE](LICENSE) 文件，并授予您使用本仓库中任何代码的许可，依据 [MIT 许可证](https://opensource.org/licenses/MIT)，请参阅 [LICENSE-CODE](LICENSE-CODE) 文件。

文档中提到的微软、Windows、Microsoft Azure 和/或其他微软产品及服务可能是微软在美国和/或其他国家的商标或注册商标。本项目的许可证不授予您使用任何微软名称、标识或商标的权利。微软的一般商标指南可以在 http://go.microsoft.com/fwlink/?LinkID=254653 找到。

隐私信息可以在 https://go.microsoft.com/fwlink/?LinkId=521839 找到。

微软及任何贡献者保留所有其他权利，无论是根据各自的版权、专利或商标，是否通过暗示、禁止反悔或其他方式。

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ 返回顶部 ↑
  </a>
</p>



