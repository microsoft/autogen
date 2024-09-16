<a name="readme-top"></a>

<div align="center">

<img src="https://microsoft.github.io/autogen/img/ag.svg" alt="AutoGen Logo" width="100">

![Python Version](https://img.shields.io/badge/3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue) [![PyPI version](https://img.shields.io/badge/PyPI-v0.2.34-blue.svg)](https://pypi.org/project/pyautogen/)
[![NuGet version](https://badge.fury.io/nu/AutoGen.Core.svg)](https://badge.fury.io/nu/AutoGen.Core)

[![Downloads](https://static.pepy.tech/badge/pyautogen/week)](https://pepy.tech/project/pyautogen)
[![Discord](https://img.shields.io/discord/1153072414184452236?logo=discord&style=flat)](https://aka.ms/autogen-dc)

[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40pyautogen)](https://twitter.com/pyautogen)

</div>

# AutoGen

AutoGen is an open-source programming framework OSS framework for developing intelligent applications using AI Agents patterns. It offers an easy way to quickly build event-driven, distributed, scalable, resilient AI agent systems.  AutoGen aims to streamline the development and research of agentic AI. It offers features such as agents capable of interacting with each other, facilitates the use of various large language models (LLMs) and tool use support, autonomous and human-in-the-loop workflows, and multi-agent conversation patterns.

You can build and run your agent system locally and easily move to a distributed system in the cloud when you are ready.

> [!IMPORTANT]
> *Note for contributors and users*</b>: [microsoft/autogen](https://aka.ms/autogen-gh) is the official repository of AutoGen project and it is under active development and maintenance under MIT license. We welcome contributions from developers and organizations worldwide. Our goal is to foster a collaborative and inclusive community where diverse perspectives and expertise can drive innovation and enhance the project's capabilities. We acknowledge the invaluable contributions from our existing contributors, as listed in [contributors.md](./CONTRIBUTORS.md). Whether you are an individual contributor or represent an organization, we invite you to join us in shaping the future of this project. For further information please also see [Microsoft open-source contributing guidelines](https://github.com/microsoft/autogen?tab=readme-ov-file#contributing).
>
> -_*Maintainers (Sept 6th, 2024)*

AutoGen was created out of collaborative [research](https://microsoft.github.io/autogen/docs/Research) from Microsoft, Penn State University, and the University of Washington.

## Key Aspects

- Asynchronous messaging: Agents communicate with each other through asynchronous messages, enabling event-driven and request/response communication models.
- Scalable & Distributed: Enable complex scenarios with networks of agents across org boundaries
- Modular, extensible & highly customizable: E.g. custom agents, memory as a service, tools registry, model library
- x-lang support: Python & Dotnet interoperating agents today, others coming soon
- Observable, traceable & debuggable

## Getting Started

The current stable release of autogen is autogen 0.2 You can find it here: *TODO: insert link*

The version you are looking at is a new architecture for autogen 0.5.

We are in the early stages of development for this new architecture, but we are excited to share our progress with you.

We are looking for feedback and contributions to help shape the future of this project.

Your best place to start is the [Documentation](https://microsoft.github.io/agnext).

- [Documentation](http://microsoft.github.io/agnext) for the core concepts and Python API references (.NET coming).
- [Python README](https://github.com/microsoft/agnext/tree/main/python/README.md) for how to develop and test the Python package.
- [Python Examples](https://github.com/microsoft/agnext/tree/main/python/packages/autogen-core/samples) for examples of how to use the Python package and multi-agent patterns.
- [.NET](https://github.com/microsoft/agnext/tree/main/dotnet)
- [.NET Examples](https://github.com/microsoft/agnext/tree/main/dotnet/samples)

## News

:fire: **September 16, 2024**: AutoGen 0.5 is a new architecture for autogen! This new version is in preview release and being developed in the open over the next several weeks as we refine the documentation, samples, and work with our users on evolving this new version. 🚀

- Autogen 0.5 represents a rearchitecutre of the system to make it more scalable, resilient, and interoperable across multiple programming languages.
- It is designed to be more modular and extensible, with a focus on enabling a wide range of applications and use cases.
- This redeign features a full .NET SDK and python SDKs, with more languages to come in the future.  Agents may be written in either language and interoperate with one another over a common messaging protocol using the CloudEvents standard.

:tada: June 6, 2024: WIRED publishes a new article on AutoGen: [Chatbot Teamwork Makes the AI Dream Work](https://www.wired.com/story/chatbot-teamwork-makes-the-ai-dream-work/) based on interview with [Adam Fourney](https://github.com/afourney).

:tada: June 4th, 2024: Microsoft Research Forum publishes new update and video on [AutoGen and Complex Tasks](https://www.microsoft.com/en-us/research/video/autogen-update-complex-tasks-and-agents/) presented by [Adam Fourney](https://github.com/afourney).

:tada: May 29, 2024: DeepLearning.ai launched a new short course [AI Agentic Design Patterns with AutoGen](https://www.deeplearning.ai/short-courses/ai-agentic-design-patterns-with-autogen), made in collaboration with Microsoft and Penn State University, and taught by AutoGen creators [Chi Wang](https://github.com/sonichi) and [Qingyun Wu](https://github.com/qingyun-wu).

:tada: May 24, 2024: Foundation Capital published an article on [Forbes: The Promise of Multi-Agent AI](https://www.forbes.com/sites/joannechen/2024/05/24/the-promise-of-multi-agent-ai/?sh=2c1e4f454d97) and a video [AI in the Real World Episode 2: Exploring Multi-Agent AI and AutoGen with Chi Wang](https://www.youtube.com/watch?v=RLwyXRVvlNk).

:tada: May 13, 2024: [The Economist](https://www.economist.com/science-and-technology/2024/05/13/todays-ai-models-are-impressive-teams-of-them-will-be-formidable) published an article about multi-agent systems (MAS) following a January 2024 interview with [Chi Wang](https://github.com/sonichi).

:tada: May 11, 2024: [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://openreview.net/pdf?id=uAjxFFing2) received the best paper award at the [ICLR 2024 LLM Agents Workshop](https://llmagents.github.io/).

:tada: Apr 26, 2024: [AutoGen.NET](https://microsoft.github.io/autogen-for-net/) is available for .NET developers! Thanks [XiaoYun Zhang](https://www.linkedin.com/in/xiaoyun-zhang-1b531013a/)

:tada: Apr 17, 2024: Andrew Ng cited AutoGen in [The Batch newsletter](https://www.deeplearning.ai/the-batch/issue-245/) and [What's next for AI agentic workflows](https://youtu.be/sal78ACtGTc?si=JduUzN_1kDnMq0vF) at Sequoia Capital's AI Ascent (Mar 26).

:tada: Mar 3, 2024: What's new in AutoGen? 📰[Blog](https://microsoft.github.io/autogen/blog/2024/03/03/AutoGen-Update); 📺[Youtube](https://www.youtube.com/watch?v=j_mtwQiaLGU).

:tada: Mar 1, 2024: the first AutoGen multi-agent experiment on the challenging [GAIA](https://huggingface.co/spaces/gaia-benchmark/leaderboard) benchmark achieved the No. 1 accuracy in all the three levels.

<!-- :tada: Jan 30, 2024: AutoGen is highlighted by Peter Lee in Microsoft Research Forum [Keynote](https://t.co/nUBSjPDjqD). -->

:tada: Dec 31, 2023: [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework](https://arxiv.org/abs/2308.08155) is selected by [TheSequence: My Five Favorite AI Papers of 2023](https://thesequence.substack.com/p/my-five-favorite-ai-papers-of-2023).

<!-- :fire: Nov 24: pyautogen [v0.2](https://github.com/microsoft/autogen/releases/tag/v0.2.0) is released with many updates and new features compared to v0.1.1. It switches to using openai-python v1. Please read the [migration guide](https://microsoft.github.io/autogen/docs/Installation#python). -->

<!-- :fire: Nov 11: OpenAI's Assistants are available in AutoGen and interoperatable with other AutoGen agents! Checkout our [blogpost](https://microsoft.github.io/autogen/blog/2023/11/13/OAI-assistants) for details and examples. -->

:tada: Nov 8, 2023: AutoGen is selected into [Open100: Top 100 Open Source achievements](https://www.benchcouncil.org/evaluation/opencs/annual.html) 35 days after spinoff from [FLAML](https://github.com/microsoft/FLAML).

<!-- :tada: Nov 6, 2023: AutoGen is mentioned by Satya Nadella in a [fireside chat](https://youtu.be/0pLBvgYtv6U). -->

<!-- :tada: Nov 1, 2023: AutoGen is the top trending repo on GitHub in October 2023. -->

<!-- :tada: Oct 03, 2023: AutoGen spins off from [FLAML](https://github.com/microsoft/FLAML) on GitHub. -->

<!-- :tada: Aug 16: Paper about AutoGen on [arxiv](https://arxiv.org/abs/2308.08155). -->

:tada: Mar 29, 2023: AutoGen is first created in [FLAML](https://github.com/microsoft/FLAML).

<!--
:fire: FLAML is highlighted in OpenAI's [cookbook](https://github.com/openai/openai-cookbook#related-resources-from-around-the-web).

:fire: [autogen](https://microsoft.github.io/autogen/) is released with support for ChatGPT and GPT-4, based on [Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference](https://arxiv.org/abs/2303.04673).

:fire: FLAML supports Code-First AutoML & Tuning – Private Preview in [Microsoft Fabric Data Science](https://learn.microsoft.com/en-us/fabric/data-science/). -->

</details>

## Roadmaps

- [AutoGen 0.2] - This is the current stable release of AutoGen. We will continue to accept bug fixes and minor enhancements to this version.  
- [AutoGen 0.5] - This is the first release of the new event-driven architecture. This release is still in preview.  We will be focusing on stability of the interfaces, documentation, tutorials, samples, and a collection of base agents from which you can inherit. We are also working on compatibility interfaces for those familiar with prior versions of AutoGen.
- [future] - We are excited to work with our community to define the future of AutoGen. We are looking for feedback and contributions to help shape the future of this project.Here are some major planned items:
  - [ ] Add support for more languages
  - [ ] Add support for more base agents and patterns
  - [ ] Add compatibility with Bot Framework Activity Protocol
  
## Quickstart

The easiest way to start playing is
1. Click below to use the GitHub Codespace

    [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/autogen?quickstart=1)

 2. Copy OAI_CONFIG_LIST_sample to ./notebook folder, name to OAI_CONFIG_LIST, and set the correct configuration.
 3. Start playing with the notebooks!

*NOTE*: OAI_CONFIG_LIST_sample lists GPT-4 as the default model, as this represents our current recommendation, and is known to work well with AutoGen. If you use a model other than GPT-4, you may need to revise various system prompts (especially if using weaker models like GPT-3.5-turbo). Moreover, if you use models other than those hosted by OpenAI or Azure, you may incur additional risks related to alignment and safety. Proceed with caution if updating this default.

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## [Installation](https://microsoft.github.io/autogen/docs/Installation)
### Option 1. Install and Run AutoGen in Docker

Find detailed instructions for users [here](https://microsoft.github.io/autogen/docs/installation/Docker#step-1-install-docker), and for developers [here](https://microsoft.github.io/autogen/docs/Contribute#docker-for-development).

### Option 2. Install AutoGen Locally

AutoGen requires **Python version >= 3.8, < 3.13**. It can be installed from pip:

```bash
pip install pyautogen
```

Minimal dependencies are installed without extra options. You can install extra options based on the feature you need.

<!-- For example, use the following to install the dependencies needed by the [`blendsearch`](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function#blendsearch-economical-hyperparameter-optimization-with-blended-search-strategy) option.
```bash
pip install "pyautogen[blendsearch]"
``` -->

Find more options in [Installation](https://microsoft.github.io/autogen/docs/Installation#option-2-install-autogen-locally-using-virtual-environment).

<!-- Each of the [`notebook examples`](https://github.com/microsoft/autogen/tree/main/notebook) may require a specific option to be installed. -->

Even if you are installing and running AutoGen locally outside of docker, the recommendation and default behavior of agents is to perform [code execution](https://microsoft.github.io/autogen/docs/FAQ/#code-execution) in docker. Find more instructions and how to change the default behaviour [here](https://microsoft.github.io/autogen/docs/Installation#code-execution-with-docker-(default)).

For LLM inference configurations, check the [FAQs](https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints).

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Documentation

You can find detailed documentation about AutoGen [here](https://microsoft.github.io/autogen/).

In addition, you can find:

- [Research](https://microsoft.github.io/autogen/docs/Research), [blogposts](https://microsoft.github.io/autogen/blog) around AutoGen, and [Transparency FAQs](https://github.com/microsoft/autogen/blob/main/TRANSPARENCY_FAQS.md)

- [Discord](https://aka.ms/autogen-dc)

- [Contributing guide](https://microsoft.github.io/autogen/docs/Contribute)

- [Roadmap](https://github.com/orgs/microsoft/projects/989/views/3)

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Related Papers

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
    ↑ Back to Top ↑
  </a>
</p>

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

If you are new to GitHub, [here](https://opensource.guide/how-to-contribute/#how-to-submit-a-contribution) is a detailed help source on getting involved with development on GitHub.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information, see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Contributors Wall
<a href="https://github.com/microsoft/autogen/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=microsoft/autogen&max=204" />
</a>

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

# Legal Notices

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
