# Magentic-One

> Magentic-One is now available as part of the `autogen-agentchat` library.
> Please see the [user guide](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/magentic-one.html) for information.

> Looking for the original implementation of Magentic-One? It is available [here](https://github.com/microsoft/autogen/tree/v0.4.4/python/packages/autogen-magentic-one).

[Magentic-One](https://aka.ms/magentic-one-blog) is a generalist multi-agent system for solving open-ended web and file-based tasks across a variety of domains. It represents a significant step forward for multi-agent systems, achieving competitive performance on a number of agentic benchmarks (see the [technical report](https://arxiv.org/abs/2411.04468) for full details).

When originally released in [November 2024](https://aka.ms/magentic-one-blog) Magentic-One was [implemented directly on the `autogen-core` library](https://github.com/microsoft/autogen/tree/v0.4.4/python/packages/autogen-magentic-one). We have now ported Magentic-One to use `autogen-agentchat`, providing a more modular and easier to use interface. To this end, the older implementation is deprecated, but can be accessed at [https://github.com/microsoft/autogen/tree/v0.4.4/python/packages/autogen-magentic-one](https://github.com/microsoft/autogen/tree/v0.4.4/python/packages/autogen-magentic-one).

Moving forward, the Magentic-One orchestrator [MagenticOneGroupChat](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.teams.html#autogen_agentchat.teams.MagenticOneGroupChat) is now simply an AgentChat team, supporting all standard AgentChat agents and features. Likewise, Magentic-One's [MultimodalWebSurfer](https://microsoft.github.io/autogen/stable/reference/python/autogen_ext.agents.web_surfer.html#autogen_ext.agents.web_surfer.MultimodalWebSurfer), [FileSurfer](https://microsoft.github.io/autogen/stable/reference/python/autogen_ext.agents.file_surfer.html#autogen_ext.agents.file_surfer.FileSurfer), and [MagenticOneCoderAgent](https://microsoft.github.io/autogen/stable/reference/python/autogen_ext.teams.magentic_one.html) agents are now broadly available as AgentChat agents, to be used in any AgentChat workflows.

Lastly, there is a helper class, [MagenticOne](https://microsoft.github.io/autogen/stable/reference/python/autogen_ext.teams.magentic_one.html#autogen_ext.teams.magentic_one.MagenticOne), which bundles all of this together as it was in the paper with minimal configuration

## Citation

```
@misc{fourney2024magenticonegeneralistmultiagentsolving,
      title={Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks},
      author={Adam Fourney and Gagan Bansal and Hussein Mozannar and Cheng Tan and Eduardo Salinas and Erkang and Zhu and Friederike Niedtner and Grace Proebsting and Griffin Bassman and Jack Gerrits and Jacob Alber and Peter Chang and Ricky Loynd and Robert West and Victor Dibia and Ahmed Awadallah and Ece Kamar and Rafah Hosn and Saleema Amershi},
      year={2024},
      eprint={2411.04468},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2411.04468},
}
```
