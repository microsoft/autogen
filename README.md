
# Ai Agents

Build a Dev Team using event driven agents. 
This project is an experiment and is not intended to be used in production.

# Background - initial idea

From a natural language specification, set out to integrate a team of AI agents into your team’s dev process, either for discrete tasks on an existing repo (unit tests, pipeline expansions, PRs for specific intents), developing a new feature, or even building an application from scratch.  Starting from an existing repo and a broad statement of intent, work with multiple AI agents, each of which has a different emphasis - from architecture, to task breakdown, to plans for individual tasks, to code output, code review, efficiency, documentation, build, writing tests, setting up pipelines, deployment, integration tests, and then validation.
The system will present a view that facilitates chain-of-thought coordination across multiple trees of reasoning with the dev team agents.

# Emerging framework - Ai Agents

While building the dev team agents, we stumbled upon few patterns and abstractions that we think are usefull for building a variety of agentic systems.
At the moment they reside in `src/libs/Microsoft.AI.DevTeam`, but we plan to move them to a separate repo and nuget package.

# Github dev agents demo

https://github.com/microsoft/azure-openai-dev-skills-orchestrator/assets/10728102/cafb1546-69ab-4c27-aaf5-1968313d637f

## How it works

* User begins with creating an issue and then stateing what they want to accomplish, natural language, as simple or as detailed as needed.
* Product manager agent will respond with a Readme, which can be iterated upon.
  * User approves the readme or gives feedback via issue comments.
  * Once the readme is approved, the user closes the issue and the Readme is commited to a PR.
* Developer lead agent responds with a decomposed plan for development, which also can be iterated upon.
  * User approves the plan or gives feedback via issue comments.
  * Once the readme is approved, the user closes the issue and the plan is used to break down the task to different developer agents.
* Developer agents respond with code, which can be iterated upon.
  * User approves the code or gives feedback via issue comments.
  * Once the code is approved, the user closes the issue and the code is commited to a PR.

# How to run the Github dev agents project

Check [the getting started guide](./docs/github-flow-getting-started.md)

# Other scenarios using the AiAgents

## TODO

# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

# Legal Notices

Microsoft and any contributors grant you a license to the Microsoft documentation and other content
in this repository under the [Creative Commons Attribution 4.0 International Public License](https://creativecommons.org/licenses/by/4.0/legalcode),
see the [LICENSE](LICENSE) file, and grant you a license to any code in the repository under the [MIT License](https://opensource.org/licenses/MIT), see the
[LICENSE-CODE](LICENSE-CODE) file.

Microsoft, Windows, Microsoft Azure and/or other Microsoft products and services referenced in the documentation
may be either trademarks or registered trademarks of Microsoft in the United States and/or other countries.
The licenses for this project do not grant you rights to use any Microsoft names, logos, or trademarks.
Microsoft's general trademark guidelines can be found at <http://go.microsoft.com/fwlink/?LinkID=254653>.

Privacy information can be found at <https://privacy.microsoft.com/en-us/>

Microsoft and any contributors reserve all other rights, whether under their respective copyrights, patents,
or trademarks, whether by implication, estoppel or otherwise.
