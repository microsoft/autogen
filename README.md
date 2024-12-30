<a name="readme-top"></a>

<div align="center">
<img src="https://microsoft.github.io/autogen/0.2/img/ag.svg" alt="AutoGen Logo" width="100">

[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40pyautogen)](https://twitter.com/pyautogen) [![LinkedIn](https://img.shields.io/badge/LinkedIn-Company?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/105812540) [![Discord](https://img.shields.io/badge/discord-chat-green?logo=discord)](https://aka.ms/autogen-discord) [![GitHub Discussions](https://img.shields.io/badge/Discussions-Q%26A-green?logo=github)](https://github.com/microsoft/autogen/discussions) [![0.2 Docs](https://img.shields.io/badge/Docs-0.2-blue)](https://microsoft.github.io/autogen/0.2/) [![0.4 Docs](https://img.shields.io/badge/Docs-0.4-blue)](https://microsoft.github.io/autogen/dev/)

[![PyPi autogen-core](https://img.shields.io/badge/PyPi-autogen--core-blue?logo=pypi)](https://pypi.org/project/autogen-core/0.4.0.dev12/) [![PyPi autogen-agentchat](https://img.shields.io/badge/PyPi-autogen--agentchat-blue?logo=pypi)](https://pypi.org/project/autogen-agentchat/0.4.0.dev12/) [![PyPi autogen-ext](https://img.shields.io/badge/PyPi-autogen--ext-blue?logo=pypi)](https://pypi.org/project/autogen-ext/0.4.0.dev12/)
</div>

# AutoGen

> [!IMPORTANT]
>
> - (12/19/24) Hello!
The majority of the AutoGen Team members will be resting and recharging with family and friends over the holiday period. Activity/responses on the project may be delayed during the period of Dec 20-Jan 06. We will be excited to engage with you in the new year!
> - (12/11/24) We have created a new Discord server for the AutoGen community. Join us at [aka.ms/autogen-discord](https://aka.ms/autogen-discord).
> - (11/14/24) ⚠️ In response to a number of asks to clarify and distinguish between official AutoGen and its forks that created confusion, we issued a [clarification statement](https://github.com/microsoft/autogen/discussions/4217).
> - (10/13/24) Interested in the standard AutoGen as a prior user? Find it at the actively-maintained *AutoGen* [0.2 branch](https://github.com/microsoft/autogen/tree/0.2) and `autogen-agentchat~=0.2` PyPi package.
> - (10/02/24) [AutoGen 0.4](https://microsoft.github.io/autogen/dev) is a from-the-ground-up rewrite of AutoGen. Learn more about the history, goals and future at [this blog post](https://microsoft.github.io/autogen/blog). We’re excited to work with the community to gather feedback, refine, and improve the project before we officially release 0.4. This is a big change, so AutoGen 0.2 is still available, maintained, and developed in the [0.2 branch](https://github.com/microsoft/autogen/tree/0.2).
> - *[Join us for Community Office Hours](https://github.com/microsoft/autogen/discussions/4059)* We will host a weekly open discussion to answer questions, talk about Roadmap, etc.

AutoGen is an open-source framework for building AI agent systems.
It simplifies the creation of event-driven, distributed, scalable, and resilient agentic applications.
It allows you to quickly build systems where AI agents collaborate and perform tasks autonomously
or with human oversight.

- [Key Features](#key-features)
- [API Layering](#api-layering)
- [Quickstart](#quickstart)
- [Roadmap](#roadmap)
- [FAQs](#faqs)

AutoGen streamlines AI development and research, enabling the use of multiple large language models (LLMs), integrated tools, and advanced multi-agent design patterns. You can develop and test your agent systems locally, then deploy to a distributed cloud environment as your needs grow.

## Key Features

AutoGen offers the following key features:

- **Asynchronous Messaging**: Agents communicate via asynchronous messages, supporting both event-driven and request/response interaction patterns.
- **Full type support**: use types in all interfaces and enforced type check on build, with a focus on quality and cohesiveness
- **Scalable & Distributed**: Design complex, distributed agent networks that can operate across organizational boundaries.
- **Modular & Extensible**: Customize your system with pluggable components: custom agents, tools, memory, and models.
- **Cross-Language Support**: Interoperate agents across different programming languages. Currently supports Python and .NET, with more languages coming soon.
- **Observability & Debugging**: Built-in features and tools for tracking, tracing, and debugging agent interactions and workflows, including support for industry standard observability with OpenTelemetry

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

# API Layering

AutoGen has several packages and is built upon a layered architecture.
Currently, there are three main APIs your application can target:

- [Core](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/index.html)
- [AgentChat](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/index.html)
- [Extensions](https://microsoft.github.io/autogen/dev/user-guide/extensions-user-guide/index.html)

## Core

- [Installation](https://microsoft.github.io/autogen/dev/packages/index.html#pkg-info-autogen-core)
- [Quickstart](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/quickstart.html)

The core API of AutoGen, `autogen-core`, is built following the
[actor model](https://en.wikipedia.org/wiki/Actor_model).
It supports asynchronous message passing between agents and event-based workflows.
Agents in the core layer handle and produce typed messages, using either direct messaging,
which functions like RPC, or via broadcasting to topics, which is pub-sub.
Agents can be distributed and implemented in different programming languages,
while still communicating with one another.
**Start here if you are building scalable, event-driven agentic systems.**

## AgentChat

- [Installation](https://microsoft.github.io/autogen/dev/packages/index.html#pkg-info-autogen-agentchat)
- [Quickstart](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/quickstart.html)

The AgentChat API, `autogen-agentchat`, is task driven and at a high level like AutoGen 0.2.
It allows you to define conversational agents, compose them into teams and then
use them to solve tasks.
AgentChat itself is built on the core layer, but it abstracts away much of its
low-level system concepts.
If your workflows don't fit into the AgentChat API, target core instead.
**Start here if you just want to focus on quickly getting started with multi-agents workflows.**

## Extensions

The extension package `autogen-ext` contains implementations of the core interfaces using 3rd party systems,
such as OpenAI model client and Azure code executors.
Besides the built-in extensions, the package accommodates community-contributed
extensions through namespace sub-packages.
We look forward to your contributions!

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Quickstart

### Python (AgentChat)

First install the packages:

```bash
pip install "autogen-agentchat==0.4.0.dev12" "autogen-ext[openai]==0.4.0.dev12"
```

The following code uses OpenAI's GPT-4o model and you need to provide your
API key to run.
To use Azure OpenAI models, follow the instruction
[here](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/cookbook/azure-openai-with-aad-auth.html).

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Define a tool
async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."

async def main() -> None:
    # Define an agent
    weather_agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-2024-08-06",
            # api_key="YOUR_API_KEY",
        ),
        tools=[get_weather],
    )

    # Define termination condition
    termination = TextMentionTermination("TERMINATE")

    # Define a team
    agent_team = RoundRobinGroupChat([weather_agent], termination_condition=termination)

    # Run the team and stream messages to the console
    stream = agent_team.run_stream(task="What is the weather in New York?")
    await Console(stream)

asyncio.run(main())
```

### C\#

The .NET SDK does not yet support all of the interfaces that the python SDK offers but we are working on bringing them to parity.
To use the .NET SDK, you need to add a package reference to the src in your project.
We will release nuget packages soon and will update these instructions when that happens.

```
git clone https://github.com/microsoft/autogen.git
cd autogen
# Switch to the branch that has this code
git switch staging-dev
# Build the project
cd dotnet && dotnet build AutoGen.sln
# In your source code, add AutoGen to your project
dotnet add <your.csproj> reference <path to your checkout of autogen>/dotnet/src/Microsoft.AutoGen/Core/Microsoft.AutoGen.Core.csproj
```

Then, define and run your first agent:

```csharp
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

// send a message to the agent
var app = await App.PublishMessageAsync("HelloAgents", new NewMessageReceived
{
    Message = "World"
}, local: true);

await App.RuntimeApp!.WaitForShutdownAsync();
await app.WaitForShutdownAsync();

[TopicSubscription("agents")]
public class HelloAgent(
    IAgentContext worker,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : ConsoleAgent(
        worker,
        typeRegistry),
        ISayHello,
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>
{
    public async Task Handle(NewMessageReceived item)
    {
        var response = await SayHello(item.Message).ConfigureAwait(false);
        var evt = new Output
        {
            Message = response
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEventAsync(evt).ConfigureAwait(false);
        var goodbye = new ConversationClosed
        {
            UserId = this.AgentId.Key,
            UserMessage = "Goodbye"
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEventAsync(goodbye).ConfigureAwait(false);
    }
    public async Task Handle(ConversationClosed item)
    {
        var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
        var evt = new Output
        {
            Message = goodbye
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEventAsync(evt).ConfigureAwait(false);
        await Task.Delay(60000);
        await App.ShutdownAsync();
    }
    public async Task<string> SayHello(string ask)
    {
        var response = $"\n\n\n\n***************Hello {ask}**********************\n\n\n\n";
        return response;
    }
}
public interface ISayHello
{
    public Task<string> SayHello(string ask);
}
```

```bash
dotnet run
```

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## Roadmap

- AutoGen 0.2 - This is the current stable release of AutoGen. We will continue to accept bug fixes and minor enhancements to this version.
- AutoGen 0.4 - This is the first release of the new architecture. This release is still in *preview*. We will be focusing on the stability of the interfaces, documentation, tutorials, samples, and a collection of built-in agents which you can use. We are excited to work with our community to define the future of AutoGen. We are looking for feedback and contributions to help shape the future of this project. Here are some major planned items:
  - More programming languages (e.g., TypeScript)
  - More built-in agents and multi-agent workflows
  - Deployment of distributed agents
  - Re-implementation/migration of AutoGen Studio
  - Integration with other agent frameworks and data sources
  - Advanced RAG techniques and memory services

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>

## FAQs

### What is AutoGen 0.4?

AutoGen v0.4 is a rewrite of AutoGen from the ground up to create a more robust,
scalable, easier to use, cross-language library for building AI Agents.
Some key features include asynchronous messaging, support for scalable distributed agents,
modular extensible design (bring your own agents, implement behaviors however you like),
cross-language support, improved observability, and full typing integration.
It is a breaking change.

### Why these changes?

We listened to our AutoGen users, learned from what was working, and adapted to fix what wasn't.
We brought together wide-ranging teams working on many different types of AI Agents
and collaborated to design an improved framework with a more flexible
programming model and better scalability.

### Is this project still maintained?

We want to reaffirm our commitment to supporting both the original version of AutoGen (0.2) and the redesign (0.4) . AutoGen 0.4 is still work-in-progress, and we shared the code now to build with the community. There are no plans to deprecate the original AutoGen anytime soon, and both versions will be actively maintained.

### Who should use it 0.4?

This code is still experimental, so expect changes and bugs while we work towards a stable 0.4 release. We encourage early adopters to
try it out, give us feedback, and contribute.
For those looking for a stable version we recommend to continue using 0.2

### I'm using AutoGen 0.2, should I upgrade?

If you consider yourself an early adopter, you are comfortable making some
changes to your code, and are willing to try it out, then yes.

### How do I still use AutoGen 0.2?

AutoGen 0.2 can be installed with:

```sh
pip install autogen-agentchat~=0.2
```

### Will AutoGen Studio be supported in 0.4?

Yes, this is on the [roadmap](#roadmap).
Our current plan is to enable an implementation of AutoGen Studio
on the AgentChat high level API which implements a set of agent functionalities
(agents, teams, etc).

### How do I migrate?

For users familiar with AutoGen, the AgentChat library in 0.4 provides similar concepts.
We are working on a migration guide.

### Is 0.4 done?

We are still actively developing AutoGen 0.4. One exciting new feature is the emergence of new SDKs for .NET. The python SDKs are further ahead at this time but our goal is to achieve parity. We aim to add additional languages in future releases.

### What is happening next? When will this release be ready?

We are still working on improving the documentation, samples, and enhancing the code. We are hoping to release before the end of the year when things are ready.

### What is the history of this project?

The rearchitecture of the framework started with multiple Microsoft teams coming together
to address the gaps and learnings from AutoGen 0.2 - merging ideas from several predecessor projects.
The team worked on this internally for some time to ensure alignment before moving work back to the open in October 2024.

### What is the official channel for support?

Use GitHub [Issues](https://github.com/microsoft/autogen/issues) for bug reports and feature requests.
Use GitHub [Discussions](https://github.com/microsoft/autogen/discussions) for general questions and discussions.

### Do you use Discord for communications?

We are unable to use the old Discord for project discussions, many of the maintainers no longer have viewing or posting rights there. Therefore, we request that all discussions take place on <https://github.com/microsoft/autogen/discussions/>  or the [new discord server](https://aka.ms/autogen-discord).

### What about forks?

<https://github.com/microsoft/autogen/> remains the only official repo for development and support of AutoGen.
We are aware that there are thousands of forks of AutoGen, including many for personal development and startups building with or on top of the library. We are not involved with any of these forks and are not aware of any plans related to them.

### What is the status of the license and open source?

Our project remains fully open-source and accessible to everyone. We understand that some forks use different licenses to align with different interests. We will continue to use the most permissive license (MIT) for the project.

### Can you clarify the current state of the packages?

Currently, we are unable to make releases to the `pyautogen` package via Pypi due to a change to package ownership that was done without our involvement. Additionally, we are moving to using multiple packages to align with the new design. Please see details [here](https://microsoft.github.io/autogen/dev/packages/index.html).

### Can I still be involved?

We are grateful to all the contributors to AutoGen 0.2 and we look forward to continuing to collaborate with everyone in the AutoGen community.

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
Microsoft's general trademark guidelines can be found at <http://go.microsoft.com/fwlink/?LinkID=254653>.

Privacy information can be found at <https://go.microsoft.com/fwlink/?LinkId=521839>

Microsoft and any contributors reserve all other rights, whether under their respective copyrights, patents,
or trademarks, whether by implication, estoppel, or otherwise.

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>
