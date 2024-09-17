<a name="readme-top"></a>

<div align="right">

[![PyPI version](https://img.shields.io/badge/PyPI-v0.2.34-blue.svg)](https://pypi.org/project/pyautogen/)
[![NuGet version](https://badge.fury.io/nu/AutoGen.Core.svg)](https://badge.fury.io/nu/AutoGen.Core)[![Discord](https://img.shields.io/discord/1153072414184452236?logo=discord&style=flat)](https://aka.ms/autogen-dc)[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40pyautogen)](https://twitter.com/pyautogen)

</div>

# AutoGen

> <sup><sub>[!IMPORTANT]</sup></sup>
> <sup><sub>*Note for contributors and users*</b>: [microsoft/autogen](https://aka.ms/autogen-gh) is the official repository of AutoGen project and it is under active development and maintenance under MIT license. We welcome contributions from developers and organizations worldwide. Our goal is to foster a collaborative and inclusive community where diverse perspectives and expertise can drive innovation and enhance the project's capabilities. We acknowledge the invaluable contributions from our existing contributors, as listed in [contributors.md](./CONTRIBUTORS.md). Whether you are an individual contributor or represent an organization, we invite you to join us in shaping the future of this project. For further information please also see [Microsoft open-source contributing guidelines](https://github.com/microsoft/autogen?tab=readme-ov-file#contributing).</sub></sup>
>
> <sup><sub>-*Maintainers (Sept 6th, 2024)*</sub></sup>

AutoGen is an open-source framework for building intelligent, agent-based systems using AI. It simplifies the creation of event-driven, distributed, scalable, and resilient AI applications. With AutoGen, you can easily design systems where AI agents collaborate, interact, and perform tasks autonomously or with human oversight.

* [Installation](#install)
* [Features](#features)
* [Using Autogen](#using-autogen)
* [Roadmap](#roadmap)

AutoGen is built to streamline AI development and research, enabling the use of multiple large language models (LLMs), integrated tools, and advanced multi-agent communication workflows.
You can develop and test your agent systems locally, then seamlessly scale to a distributed cloud environment as your needs grow.

:fire: **September 18, 2024**: AutoGen 0.5 is a new architecture for autogen! This new version is in preview release and being developed in the open over the next several weeks as we refine the documentation, samples, and work with our users on evolving this new version. 🚀

- Autogen 0.5 represents a rearchitecutre of the system to make it more scalable, resilient, and interoperable across multiple programming languages.
- It is designed to be more modular and extensible, with a focus on enabling a wide range of applications and use cases.
- This redeign features a full .NET SDK and python SDKs, with more languages to come in the future.  Agents may be written in either language and interoperate with one another over a common messaging protocol using the CloudEvents standard.

# Install

<div align="center">

[(See Installation docs formore details)](https://microsoft.github.io/autogen/docs/Installation)

</div>

#### Option 1. Install and Run AutoGen in Docker

Find detailed instructions for users [here](https://microsoft.github.io/autogen/docs/installation/Docker#step-1-install-docker), and for developers [here](https://microsoft.github.io/autogen/docs/Contribute#docker-for-development).

#### Option 2. Install AutoGen Locally

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

# Features

- **Asynchronous Messaging**: Agents communicate via asynchronous messages, supporting both event-driven and request/response interaction patterns.
- **Scalable & Distributed**: Design complex, distributed agent networks that can operate across organizational boundaries.
- **Modular & Extensible**: Customize your system with pluggable components, including custom agents, memory services, tool registries, and model libraries.
- **Cross-Language Support**: Interoperate agents across different programming languages. Currently supports Python and .NET, with more languages coming soon.
- **Observability & Debugging**: Built-in tools for tracking, tracing, and debugging agent interactions and workflows.

# Using Autogen

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

You can find detailed documentation about AutoGen [here](https://microsoft.github.io/autogen/).

In addition, you can find:

- [Research](https://microsoft.github.io/autogen/docs/Research), [blogposts](https://microsoft.github.io/autogen/blog) around AutoGen, and [Transparency FAQs](https://github.com/microsoft/autogen/blob/main/TRANSPARENCY_FAQS.md)

- [Discord](https://aka.ms/autogen-dc)

- [Contributing guide](https://microsoft.github.io/autogen/docs/Contribute)

# Roadmap

- [AutoGen 0.2] - This is the current stable release of AutoGen. We will continue to accept bug fixes and minor enhancements to this version.  
- [AutoGen 0.5] - This is the first release of the new event-driven architecture. This release is still in preview.  We will be focusing on stability of the interfaces, documentation, tutorials, samples, and a collection of base agents from which you can inherit. We are also working on compatibility interfaces for those familiar with prior versions of AutoGen.
- [future] - We are excited to work with our community to define the future of AutoGen. We are looking for feedback and contributions to help shape the future of this project.Here are some major planned items:
  - [ ] Add support for more languages
  - [ ] Add support for more base agents and patterns
  - [ ] Add compatibility with Bot Framework Activity Protocol

# FAQ

### What is AutoGen 0.5?

AutoGen 0.5 is a rewrite of autogen from the ground up to create a more robust, scalable, easier to use, x-lang SDK for building AI Agents.  

### Why are you doing this?

We listened to our AutoGen users, learned from what was working, and adapted to fix what wasn't. We brought together wide ranging teams working on many different types of AI Agents and collaborated to design an improved framework with a more flexible programming model and better scaleability. 

### Who should use it?

This code is still experimental. We encourage adventurous early adopters to please try it out, give us feedback, and contribute. 

### I'm using AutoGen 0.2, should I upgrade?

If you consider yourself an early adopter, you are comfortable making some changes to your code, and are willing to try it out, then yes. 

### How do I still use AutoGen 0.2?

Just keep doing what you were doing before. 

### How do I migrate?

We are working on a migration guide. Until then, see the [documentation]((http://microsoft.github.io/agnext)

### What is happening next? When will this release be ready?

We are still working on improving the documentation, samples, and enhancing the code. We will prepare a release announcement when these things are completed in the next few weeks. 

### What is the history of this project?

The rearchitecture of autogen came from multiple Microsoft teams coming together to build the next generation of AI agent framework - merging ideas from several predecessor projects. The team decided to bring this work to OSS as an evolutionof autogen in September 2024. 

### What are the official channels for support?

You can use the same support channels as for AutoGen 0.2 - The GH project[Issues](https://github.com/microsoft/agnext/issues) and [Discord](https://aka.ms/autogen-dc). 

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

AutoGen was created out of collaborative [research](https://microsoft.github.io/autogen/docs/Research) from Microsoft, Penn State University, and the University of Washington.