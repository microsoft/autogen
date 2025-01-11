## AutoGen FAQs

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

We want to reaffirm our commitment to supporting both the original version of AutoGen (0.2) and the redesign (0.4). AutoGen 0.4 is still work-in-progress, and we shared the code now to build with the community. There are no plans to deprecate the original AutoGen anytime soon, and both versions will be actively maintained.

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
